import os
import subprocess
import shutil
import json
import sqlite3
import asyncio
from datetime import datetime
from fastapi import FastAPI, HTTPException, UploadFile, File, Query
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
os.makedirs("public/subtitles", exist_ok=True)

# ===== FFMPEG AUTO-DETECTION =====
def find_ffmpeg():
    """Search for ffmpeg in known locations."""
    path = shutil.which("ffmpeg")
    if path:
        return path
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
    ff = find_ffmpeg()
    if ff:
        probe = ff.replace("ffmpeg.exe", "ffprobe.exe").replace("ffmpeg", "ffprobe")
        if os.path.isfile(probe):
            return probe
    return None

FFMPEG_PATH = find_ffmpeg()
FFPROBE_PATH = find_ffprobe()

# ===== AI MODULE (lazy import) =====
ai = None
def get_ai():
    global ai
    if ai is None:
        try:
            import ai_module
            ai = ai_module
            print("[INIT] AI module loaded successfully")
        except Exception as e:
            print(f"[INIT] AI module unavailable: {e}")
    return ai

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
            status TEXT DEFAULT 'processing',
            ai_mode TEXT DEFAULT 'smart'
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS shorts (
            id TEXT PRIMARY KEY,
            project_id TEXT,
            video_url TEXT,
            thumbnail_url TEXT,
            subtitle_url TEXT,
            start_time TEXT,
            duration TEXT,
            clip_index INTEGER,
            ai_reason TEXT,
            has_captions INTEGER DEFAULT 0,
            created_at TEXT,
            FOREIGN KEY (project_id) REFERENCES projects(id)
        )
    """)
    # Add columns if they don't exist (migration)
    try:
        conn.execute("ALTER TABLE shorts ADD COLUMN subtitle_url TEXT")
    except:
        pass
    try:
        conn.execute("ALTER TABLE shorts ADD COLUMN ai_reason TEXT")
    except:
        pass
    try:
        conn.execute("ALTER TABLE shorts ADD COLUMN has_captions INTEGER DEFAULT 0")
    except:
        pass
    try:
        conn.execute("ALTER TABLE projects ADD COLUMN ai_mode TEXT DEFAULT 'smart'")
    except:
        pass
    conn.commit()
    conn.close()

init_db()

# ===== APP =====
app = FastAPI(title="KortShort API", version="3.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class VideoRequest(BaseModel):
    url: str
    ai_mode: str = "smart"  # "smart" | "fast" | "manual"

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
        return 60.0
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
    """Calculate segments to cut from the video (fallback without AI)."""
    segments = []
    if duration <= 30:
        segments.append({"start": 0, "duration": min(duration, 15), "reason": "Full short video"})
        return segments

    clip_duration = 30
    if duration < 120:
        clip_duration = 20
        max_clips = min(max_clips, 3)

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
        if dur >= 5:
            segments.append({"start": round(start, 1), "duration": round(dur, 1), "reason": "Auto-selected"})

    return segments

def generate_thumbnail(video_path: str, thumb_path: str, timestamp: float = 1.0):
    """Extract a thumbnail frame from a video."""
    ffmpeg = get_ffmpeg()
    cmd = [ffmpeg, "-y", "-i", video_path, "-ss", str(timestamp), "-vframes", "1", "-vf", "scale=320:-1", thumb_path]
    subprocess.run(cmd, capture_output=True, text=True)

def process_clip(input_path: str, video_id: str, clip_index: int,
                 start: float, duration: float,
                 subtitle_path: str = None, crop_filter: str = None) -> dict:
    """Process a single clip: crop to 9:16 + optional captions."""
    ffmpeg = get_ffmpeg()
    output_path = f"public/outputs/{video_id}_clip_{clip_index}.mp4"
    thumb_path = f"public/thumbnails/{video_id}_clip_{clip_index}.jpg"

    # Build video filter chain
    vf_parts = []

    # Smart crop or default center crop
    vf_parts.append(crop_filter or "crop=ih*9/16:ih")

    # Burn subtitles if available
    if subtitle_path and os.path.isfile(subtitle_path):
        # Escape path for FFmpeg (Windows backslashes)
        escaped = subtitle_path.replace("\\", "/").replace(":", "\\\\:")
        vf_parts.append(f"ass='{escaped}'")

    vf_string = ",".join(vf_parts)

    cmd = [
        ffmpeg, "-y", "-i", input_path,
        "-ss", str(start), "-t", str(duration),
        "-vf", vf_string,
        "-c:a", "aac", "-c:v", "libx264", "-preset", "fast",
        output_path
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        # Retry without subtitles if that failed
        if subtitle_path:
            print(f"[WARN] Subtitle burn failed, retrying without: {result.stderr[-200:]}")
            cmd_simple = [
                ffmpeg, "-y", "-i", input_path,
                "-ss", str(start), "-t", str(duration),
                "-vf", crop_filter or "crop=ih*9/16:ih",
                "-c:a", "aac", "-c:v", "libx264", "-preset", "fast",
                output_path
            ]
            result = subprocess.run(cmd_simple, capture_output=True, text=True)
            if result.returncode != 0:
                raise Exception(f"FFmpeg clip {clip_index} error: {result.stderr[-300:]}")
        else:
            raise Exception(f"FFmpeg clip {clip_index} error: {result.stderr[-300:]}")

    generate_thumbnail(output_path, thumb_path)

    return {
        "video_url": f"http://localhost:8000/outputs/{video_id}_clip_{clip_index}.mp4",
        "thumbnail_url": f"http://localhost:8000/thumbnails/{video_id}_clip_{clip_index}.jpg",
        "start": start,
        "duration": duration,
        "clip_index": clip_index,
        "has_captions": subtitle_path is not None and os.path.isfile(subtitle_path)
    }

def save_project(project_id, source_url, source_file, title, ai_mode="smart"):
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "INSERT INTO projects (id, source_url, source_file, title, created_at, status, ai_mode) VALUES (?,?,?,?,?,?,?)",
        (project_id, source_url, source_file, title, datetime.now().isoformat(), "processing", ai_mode)
    )
    conn.commit()
    conn.close()

def save_short(short_id, project_id, clip, reason=""):
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "INSERT INTO shorts (id, project_id, video_url, thumbnail_url, start_time, duration, clip_index, ai_reason, has_captions, created_at) VALUES (?,?,?,?,?,?,?,?,?,?)",
        (short_id, project_id, clip["video_url"], clip["thumbnail_url"],
         str(clip["start"]), str(clip["duration"]), clip["clip_index"],
         reason, int(clip.get("has_captions", False)), datetime.now().isoformat())
    )
    conn.commit()
    conn.close()

def update_project_status(project_id, status):
    conn = sqlite3.connect(DB_PATH)
    conn.execute("UPDATE projects SET status=? WHERE id=?", (status, project_id))
    conn.commit()
    conn.close()

# ===== SSE PROGRESS =====
progress_store = {}

async def progress_generator(project_id: str):
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

# ===== AI PIPELINE =====
def run_ai_pipeline(download_path: str, project_id: str, duration: float, ai_mode: str):
    """Run the full AI pipeline: transcribe -> curate -> detect faces."""
    ai_mod = get_ai()
    segments = []
    subtitle_path = None
    crop_filter = None

    if not ai_mod or ai_mode == "fast":
        # Fallback: no AI, just auto-segments
        segments = calculate_segments(duration)
        return segments, subtitle_path, crop_filter

    # 1. Transcription (Whisper)
    try:
        progress_store[project_id] = {"step": "transcribing", "progress": 25, "status": "processing",
                                       "detail": "Whisper AI generating captions..."}
        print(f"[AI] Step 1/3: Transcribing with Whisper...")
        transcription = ai_mod.transcribe_video(download_path, model_size="base")
        full_text = transcription.get("text", "")
        print(f"[AI] Transcription: {len(full_text)} chars, {len(transcription.get('segments', []))} segments")

        # Generate subtitle file
        subtitle_path = f"public/subtitles/{project_id}.ass"
        ai_mod.generate_ass_subtitles(transcription, subtitle_path)
        print(f"[AI] Subtitles saved: {subtitle_path}")
    except Exception as e:
        print(f"[AI] Whisper error (non-fatal): {e}")
        full_text = ""

    # 2. Viral Curation (Ollama/Qwen)
    if ai_mode == "smart" and full_text:
        try:
            progress_store[project_id] = {"step": "curating", "progress": 40, "status": "processing",
                                           "detail": "AI selecting viral moments..."}
            print("[AI] Step 2/3: Ollama curating viral moments...")
            ai_segments = ai_mod.find_viral_moments(full_text, duration, model="qwen2.5:3b", max_clips=4)
            if ai_segments:
                segments = ai_segments
                print(f"[AI] Curation found {len(segments)} viral moments")
            else:
                segments = calculate_segments(duration)
                print("[AI] Curation returned empty, using auto-segments")
        except Exception as e:
            print(f"[AI] Curation error (non-fatal): {e}")
            segments = calculate_segments(duration)
    else:
        segments = calculate_segments(duration)

    # 3. Face Detection (OpenCV)
    try:
        progress_store[project_id] = {"step": "detecting", "progress": 50, "status": "processing",
                                       "detail": "Detecting faces for smart reframe..."}
        print("[AI] Step 3/3: OpenCV face detection...")
        face_positions = ai_mod.detect_face_positions(download_path, sample_interval=30)
        if face_positions:
            w, h = ai_mod.get_video_dimensions(download_path)
            crop_filter = ai_mod.build_smart_crop_filter(face_positions, w, h)
            print(f"[AI] Smart crop: {crop_filter}")
    except Exception as e:
        print(f"[AI] Face detection error (non-fatal): {e}")

    return segments, subtitle_path, crop_filter


# ===== ROUTES =====
@app.post("/process")
async def process_video(req: VideoRequest):
    project_id = str(uuid.uuid4())[:8]
    download_path = f"downloads/{project_id}.mp4"

    try:
        save_project(project_id, req.url, None, req.url[:60], req.ai_mode)
        progress_store[project_id] = {"step": "downloading", "progress": 5, "status": "processing"}

        # Download
        print(f"[DL] Downloading: {req.url}")
        ydl_opts = {
            'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
            'outtmpl': download_path,
            'quiet': True,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(req.url, download=True)
            video_title = info.get('title', req.url[:40])

        conn = sqlite3.connect(DB_PATH)
        conn.execute("UPDATE projects SET title=? WHERE id=?", (video_title, project_id))
        conn.commit()
        conn.close()

        print(f"[DL] Downloaded: {video_title}")
        progress_store[project_id] = {"step": "analyzing", "progress": 15, "status": "processing"}

        duration = get_video_duration(download_path)

        # AI Pipeline
        segments, subtitle_path, crop_filter = run_ai_pipeline(
            download_path, project_id, duration, req.ai_mode
        )

        print(f"[PROC] Video: {duration:.0f}s -> {len(segments)} clips")
        progress_store[project_id] = {"step": "cutting", "progress": 55, "status": "processing",
                                       "total_clips": len(segments)}

        # Process each clip
        clips = []
        for i, seg in enumerate(segments):
            start = seg.get("start", 0)
            dur = seg.get("duration", 30)
            reason = seg.get("reason", "")
            print(f"[PROC] Clip {i+1}/{len(segments)}: {start}s +{dur}s | {reason}")

            clip = process_clip(download_path, project_id, i, start, dur,
                              subtitle_path=subtitle_path, crop_filter=crop_filter)
            clip["reason"] = reason
            clips.append(clip)
            save_short(str(uuid.uuid4())[:8], project_id, clip, reason)

            pct = 55 + int((i + 1) / len(segments) * 40)
            progress_store[project_id] = {"step": "cutting", "progress": pct,
                                           "status": "processing", "current_clip": i + 1,
                                           "total_clips": len(segments)}

        update_project_status(project_id, "done")
        progress_store[project_id] = {"step": "done", "progress": 100, "status": "done"}
        print(f"[DONE] {len(clips)} clips for project {project_id}")

        return {
            "status": "success",
            "project_id": project_id,
            "title": video_title,
            "ai_mode": req.ai_mode,
            "clips": clips
        }

    except Exception as e:
        print(f"[ERR] {e}")
        update_project_status(project_id, "error")
        progress_store[project_id] = {"step": "error", "progress": 0, "status": "error", "detail": str(e)}
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/upload")
async def upload_video(file: UploadFile = File(...), ai_mode: str = Query("smart")):
    project_id = str(uuid.uuid4())[:8]
    save_path = f"downloads/{project_id}.mp4"

    try:
        save_project(project_id, None, file.filename, file.filename, ai_mode)
        progress_store[project_id] = {"step": "uploading", "progress": 5, "status": "processing"}

        print(f"[UPL] Upload: {file.filename}")
        with open(save_path, "wb") as f:
            content = await file.read()
            f.write(content)

        progress_store[project_id] = {"step": "analyzing", "progress": 15, "status": "processing"}
        duration = get_video_duration(save_path)

        # AI Pipeline
        segments, subtitle_path, crop_filter = run_ai_pipeline(
            save_path, project_id, duration, ai_mode
        )

        progress_store[project_id] = {"step": "cutting", "progress": 55, "status": "processing",
                                       "total_clips": len(segments)}

        clips = []
        for i, seg in enumerate(segments):
            start = seg.get("start", 0)
            dur = seg.get("duration", 30)
            reason = seg.get("reason", "")

            clip = process_clip(save_path, project_id, i, start, dur,
                              subtitle_path=subtitle_path, crop_filter=crop_filter)
            clip["reason"] = reason
            clips.append(clip)
            save_short(str(uuid.uuid4())[:8], project_id, clip, reason)

            pct = 55 + int((i + 1) / len(segments) * 40)
            progress_store[project_id] = {"step": "cutting", "progress": pct,
                                           "status": "processing", "current_clip": i + 1,
                                           "total_clips": len(segments)}

        update_project_status(project_id, "done")
        progress_store[project_id] = {"step": "done", "progress": 100, "status": "done"}

        return {
            "status": "success",
            "project_id": project_id,
            "title": file.filename,
            "ai_mode": ai_mode,
            "clips": clips
        }

    except Exception as e:
        print(f"[ERR] Upload: {e}")
        progress_store[project_id] = {"step": "error", "progress": 0, "status": "error"}
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/history")
def get_history():
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
            "ai_mode": p["ai_mode"] if "ai_mode" in p.keys() else "fast",
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

@app.get("/ai/status")
def ai_status():
    """Check AI capabilities available."""
    ai_mod = get_ai()
    whisper_ok = False
    ollama_ok = False
    opencv_ok = False

    if ai_mod:
        try:
            import whisper
            whisper_ok = True
        except:
            pass
        try:
            import requests as req
            r = req.get("http://localhost:11434/api/tags", timeout=3)
            ollama_ok = r.status_code == 200
        except:
            pass
        try:
            import cv2
            opencv_ok = True
        except:
            pass

    return {
        "ai_available": ai_mod is not None,
        "whisper": whisper_ok,
        "ollama": ollama_ok,
        "opencv": opencv_ok,
        "ffmpeg": FFMPEG_PATH or "NOT FOUND"
    }

@app.get("/health")
def health_check():
    conn = sqlite3.connect(DB_PATH)
    project_count = conn.execute("SELECT COUNT(*) FROM projects").fetchone()[0]
    conn.close()
    return {
        "status": "ok",
        "version": "3.0.0",
        "ffmpeg": FFMPEG_PATH or "NOT FOUND",
        "ffprobe": FFPROBE_PATH or "NOT FOUND",
        "projects_count": project_count
    }

# Static files
app.mount("/outputs", StaticFiles(directory="public/outputs"), name="outputs")
app.mount("/thumbnails", StaticFiles(directory="public/thumbnails"), name="thumbnails")
app.mount("/subtitles", StaticFiles(directory="public/subtitles"), name="subtitles")

if __name__ == "__main__":
    import uvicorn
    print("[INIT] KortShort Backend v3.0 starting...")
    print(f"[INIT] FFmpeg: {FFMPEG_PATH or 'NOT FOUND!'}")
    print(f"[INIT] FFprobe: {FFPROBE_PATH or 'NOT FOUND!'}")
    print(f"[INIT] Database: {DB_PATH}")
    ai_mod = get_ai()
    if ai_mod:
        print("[INIT] AI module: READY")
    else:
        print("[INIT] AI module: UNAVAILABLE (will use fallback)")
    uvicorn.run(app, host="0.0.0.0", port=8000)
