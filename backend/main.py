import os
import subprocess
import shutil
import json
import sqlite3
import time
import asyncio
from datetime import datetime
from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import yt_dlp
import uuid

# ===== DIRECTORIES =====
os.makedirs("downloads", exist_ok=True)
os.makedirs("public/outputs", exist_ok=True)
os.makedirs("public/thumbnails", exist_ok=True)

# ===== FFMPEG AUTO-DETECTION =====
def find_ffmpeg():
    """Search for ffmpeg in known locations."""
    # 1. Check PATH first
    path = shutil.which("ffmpeg")
    if path:
        return path
    # 2. Check known local installs
    home = os.path.expanduser("~")
    candidates = [
        os.path.join(home, "mp3ok", "backend", "node_modules", "ffmpeg-static", "ffmpeg.exe"),
        os.path.join(home, "Documents", "New project", "mp3ok", "backend", "node_modules", "ffmpeg-static", "ffmpeg.exe"),
        r"C:\ffmpeg\bin\ffmpeg.exe",
        r"C:\Program Files\ffmpeg\bin\ffmpeg.exe",
    ]
    for c in candidates:
        if os.path.isfile(c):
            return c
    return None

def find_ffprobe():
    """Search for ffprobe in known locations."""
    path = shutil.which("ffprobe")
    if path:
        return path
    # Try same directory as ffmpeg
    ff = find_ffmpeg()
    if ff:
        probe = ff.replace("ffmpeg.exe", "ffprobe.exe").replace("ffmpeg", "ffprobe")
        if os.path.isfile(probe):
            return probe
    return None

FFMPEG_PATH = find_ffmpeg()
FFPROBE_PATH = find_ffprobe()

# ===== DATABASE =====
DB_PATH = "kortshort.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS projects (
            id TEXT PRIMARY KEY,
            source_url TEXT,
            source_file TEXT,
            title TEXT,
            created_at TEXT,
            status TEXT DEFAULT 'processing'
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS shorts (
            id TEXT PRIMARY KEY,
            project_id TEXT,
            video_url TEXT,
            thumbnail_url TEXT,
            start_time TEXT,
            duration TEXT,
            clip_index INTEGER,
            created_at TEXT,
            FOREIGN KEY (project_id) REFERENCES projects(id)
        )
    """)
    conn.commit()
    conn.close()

init_db()

# ===== APP =====
app = FastAPI(title="KortShort API", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class VideoRequest(BaseModel):
    url: str

# ===== HELPERS =====
def get_ffmpeg():
    if not FFMPEG_PATH:
        raise Exception("FFmpeg not found! Install it or place ffmpeg.exe in the backend folder.")
    return FFMPEG_PATH

def get_ffprobe():
    return FFPROBE_PATH

def get_video_duration(path: str) -> float:
    """Get video duration in seconds using ffprobe."""
    ffprobe = get_ffprobe()
    if not ffprobe:
        return 60.0  # fallback
    try:
        result = subprocess.run(
            [ffprobe, "-v", "quiet", "-print_format", "json", "-show_format", path],
            capture_output=True, text=True
        )
        info = json.loads(result.stdout)
        return float(info["format"]["duration"])
    except:
        return 60.0

def calculate_segments(duration: float, max_clips=4):
    """Calculate smart segments to cut from the video."""
    segments = []
    if duration <= 30:
        segments.append({"start": 0, "duration": min(duration, 15)})
        return segments

    clip_duration = 30  # seconds per clip
    if duration < 120:
        clip_duration = 20
        max_clips = min(max_clips, 3)

    # Strategy: pick start, 1/3, 2/3, and near-end positions
    positions = [0]
    if max_clips >= 2:
        positions.append(duration * 0.25)
    if max_clips >= 3:
        positions.append(duration * 0.5)
    if max_clips >= 4:
        positions.append(duration * 0.75)

    for pos in positions[:max_clips]:
        start = max(0, pos)
        dur = min(clip_duration, duration - start)
        if dur >= 5:  # minimum 5s clip
            segments.append({"start": round(start, 1), "duration": round(dur, 1)})

    return segments

def generate_thumbnail(video_path: str, thumb_path: str, timestamp: float = 1.0):
    """Extract a thumbnail frame from a video."""
    ffmpeg = get_ffmpeg()
    cmd = [
        ffmpeg, "-y", "-i", video_path,
        "-ss", str(timestamp), "-vframes", "1",
        "-vf", "scale=320:-1",
        thumb_path
    ]
    subprocess.run(cmd, capture_output=True, text=True)

def process_clip(input_path: str, video_id: str, clip_index: int,
                 start: float, duration: float) -> dict:
    """Process a single clip: crop to 9:16 vertical."""
    ffmpeg = get_ffmpeg()
    output_path = f"public/outputs/{video_id}_clip_{clip_index}.mp4"
    thumb_path = f"public/thumbnails/{video_id}_clip_{clip_index}.jpg"

    cmd = [
        ffmpeg, "-y", "-i", input_path,
        "-ss", str(start), "-t", str(duration),
        "-vf", "crop=ih*9/16:ih",
        "-c:a", "aac", "-c:v", "libx264", "-preset", "fast",
        output_path
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise Exception(f"FFmpeg clip {clip_index} error: {result.stderr[-300:]}")

    # Generate thumbnail
    generate_thumbnail(output_path, thumb_path)

    return {
        "video_url": f"http://localhost:8000/outputs/{video_id}_clip_{clip_index}.mp4",
        "thumbnail_url": f"http://localhost:8000/thumbnails/{video_id}_clip_{clip_index}.jpg",
        "start": start,
        "duration": duration,
        "clip_index": clip_index
    }

def save_project(project_id, source_url, source_file, title):
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "INSERT INTO projects (id, source_url, source_file, title, created_at, status) VALUES (?,?,?,?,?,?)",
        (project_id, source_url, source_file, title, datetime.now().isoformat(), "processing")
    )
    conn.commit()
    conn.close()

def save_short(short_id, project_id, clip):
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "INSERT INTO shorts (id, project_id, video_url, thumbnail_url, start_time, duration, clip_index, created_at) VALUES (?,?,?,?,?,?,?,?)",
        (short_id, project_id, clip["video_url"], clip["thumbnail_url"],
         str(clip["start"]), str(clip["duration"]), clip["clip_index"], datetime.now().isoformat())
    )
    conn.commit()
    conn.close()

def update_project_status(project_id, status):
    conn = sqlite3.connect(DB_PATH)
    conn.execute("UPDATE projects SET status=? WHERE id=?", (status, project_id))
    conn.commit()
    conn.close()

# ===== SSE PROGRESS STREAM =====
progress_store = {}

async def progress_generator(project_id: str):
    """Server-Sent Events generator for real-time progress."""
    while True:
        if project_id in progress_store:
            data = progress_store[project_id]
            yield f"data: {json.dumps(data)}\n\n"
            if data.get("status") in ("done", "error"):
                del progress_store[project_id]
                break
        await asyncio.sleep(0.5)

@app.get("/progress/{project_id}")
async def get_progress(project_id: str):
    return StreamingResponse(
        progress_generator(project_id),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}
    )

# ===== ROUTES =====
@app.post("/process")
async def process_video(req: VideoRequest):
    project_id = str(uuid.uuid4())[:8]
    download_path = f"downloads/{project_id}.mp4"

    try:
        # Save project
        save_project(project_id, req.url, None, req.url[:60])
        progress_store[project_id] = {"step": "downloading", "progress": 0, "status": "processing"}

        # Download
        print(f"📥 Downloading: {req.url}")
        ydl_opts = {
            'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
            'outtmpl': download_path,
            'quiet': True,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(req.url, download=True)
            video_title = info.get('title', req.url[:40])

        # Update project title
        conn = sqlite3.connect(DB_PATH)
        conn.execute("UPDATE projects SET title=? WHERE id=?", (video_title, project_id))
        conn.commit()
        conn.close()

        print(f"✅ Downloaded: {video_title}")
        progress_store[project_id] = {"step": "analyzing", "progress": 25, "status": "processing"}

        # Get duration & calculate segments
        duration = get_video_duration(download_path)
        segments = calculate_segments(duration)
        print(f"📊 Video: {duration:.0f}s → {len(segments)} clips planned")

        progress_store[project_id] = {"step": "cutting", "progress": 40, "status": "processing",
                                       "total_clips": len(segments)}

        # Process each clip
        clips = []
        for i, seg in enumerate(segments):
            print(f"✂️ Clip {i+1}/{len(segments)}: {seg['start']}s → +{seg['duration']}s")
            clip = process_clip(download_path, project_id, i, seg["start"], seg["duration"])
            clips.append(clip)
            save_short(str(uuid.uuid4())[:8], project_id, clip)

            pct = 40 + int((i + 1) / len(segments) * 50)
            progress_store[project_id] = {"step": "cutting", "progress": pct,
                                           "status": "processing", "current_clip": i + 1,
                                           "total_clips": len(segments)}

        update_project_status(project_id, "done")
        progress_store[project_id] = {"step": "done", "progress": 100, "status": "done"}
        print(f"🎬 Done! {len(clips)} clips generated for project {project_id}")

        return {
            "status": "success",
            "project_id": project_id,
            "title": video_title,
            "clips": clips
        }

    except Exception as e:
        print(f"❌ Error: {e}")
        update_project_status(project_id, "error")
        progress_store[project_id] = {"step": "error", "progress": 0, "status": "error", "detail": str(e)}
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/upload")
async def upload_video(file: UploadFile = File(...)):
    project_id = str(uuid.uuid4())[:8]
    save_path = f"downloads/{project_id}.mp4"

    try:
        save_project(project_id, None, file.filename, file.filename)
        progress_store[project_id] = {"step": "uploading", "progress": 10, "status": "processing"}

        print(f"📤 Upload: {file.filename}")
        with open(save_path, "wb") as f:
            content = await file.read()
            f.write(content)

        progress_store[project_id] = {"step": "analyzing", "progress": 30, "status": "processing"}

        duration = get_video_duration(save_path)
        segments = calculate_segments(duration)

        progress_store[project_id] = {"step": "cutting", "progress": 40, "status": "processing",
                                       "total_clips": len(segments)}

        clips = []
        for i, seg in enumerate(segments):
            clip = process_clip(save_path, project_id, i, seg["start"], seg["duration"])
            clips.append(clip)
            save_short(str(uuid.uuid4())[:8], project_id, clip)

            pct = 40 + int((i + 1) / len(segments) * 50)
            progress_store[project_id] = {"step": "cutting", "progress": pct,
                                           "status": "processing", "current_clip": i + 1,
                                           "total_clips": len(segments)}

        update_project_status(project_id, "done")
        progress_store[project_id] = {"step": "done", "progress": 100, "status": "done"}

        return {
            "status": "success",
            "project_id": project_id,
            "title": file.filename,
            "clips": clips
        }

    except Exception as e:
        print(f"❌ Upload error: {e}")
        progress_store[project_id] = {"step": "error", "progress": 0, "status": "error"}
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/history")
def get_history():
    """Get all projects with their shorts."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    projects = conn.execute("SELECT * FROM projects ORDER BY created_at DESC LIMIT 20").fetchall()
    result = []
    for p in projects:
        shorts = conn.execute("SELECT * FROM shorts WHERE project_id=? ORDER BY clip_index", (p["id"],)).fetchall()
        result.append({
            "id": p["id"],
            "title": p["title"],
            "source_url": p["source_url"],
            "created_at": p["created_at"],
            "status": p["status"],
            "clips": [dict(s) for s in shorts]
        })
    conn.close()
    return result

@app.delete("/history/{project_id}")
def delete_project(project_id: str):
    conn = sqlite3.connect(DB_PATH)
    conn.execute("DELETE FROM shorts WHERE project_id=?", (project_id,))
    conn.execute("DELETE FROM projects WHERE id=?", (project_id,))
    conn.commit()
    conn.close()
    return {"status": "deleted"}

@app.get("/health")
def health_check():
    conn = sqlite3.connect(DB_PATH)
    project_count = conn.execute("SELECT COUNT(*) FROM projects").fetchone()[0]
    conn.close()
    return {
        "status": "ok",
        "ffmpeg": FFMPEG_PATH or "NOT FOUND",
        "ffprobe": FFPROBE_PATH or "NOT FOUND",
        "projects_count": project_count
    }

# Static files
app.mount("/outputs", StaticFiles(directory="public/outputs"), name="outputs")
app.mount("/thumbnails", StaticFiles(directory="public/thumbnails"), name="thumbnails")

if __name__ == "__main__":
    import uvicorn
    print("🚀 KortShort Backend v2.0 starting...")
    print(f"📁 FFmpeg: {FFMPEG_PATH or 'NOT FOUND!'}")
    print(f"📁 FFprobe: {FFPROBE_PATH or 'NOT FOUND!'}")
    print(f"📁 Database: {DB_PATH}")
    uvicorn.run(app, host="0.0.0.0", port=8000)
