import os
import subprocess
import shutil
from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import yt_dlp
import uuid

# Ensure directories exist BEFORE app starts
os.makedirs("downloads", exist_ok=True)
os.makedirs("public/outputs", exist_ok=True)

app = FastAPI(title="KortShort API", version="1.0.0")

# Allow frontend to access the backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class VideoRequest(BaseModel):
    url: str

def process_with_ffmpeg(input_path: str, video_id: str) -> str:
    """Process video: crop to 9:16 vertical format and cut first 15s."""
    output_path = f"public/outputs/{video_id}_short.mp4"
    
    # Check if ffmpeg is available
    ffmpeg_path = shutil.which("ffmpeg")
    if not ffmpeg_path:
        raise Exception("FFmpeg not found in PATH. Please install FFmpeg and add it to your system PATH.")
    
    print(f"✂️ Cutting and cropping (9:16) with FFmpeg...")
    
    ffmpeg_cmd = [
        ffmpeg_path, "-y", "-i", input_path,
        "-t", "15",
        "-vf", "crop=ih*9/16:ih",
        "-c:a", "aac",
        "-c:v", "libx264",
        "-preset", "fast",
        output_path
    ]
    
    result = subprocess.run(ffmpeg_cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"FFmpeg stderr: {result.stderr}")
        raise Exception(f"FFmpeg error: {result.stderr[-500:]}")
    
    print(f"🎬 Processing complete: {output_path}")
    return output_path

@app.post("/process")
def process_video(req: VideoRequest):
    try:
        video_id = str(uuid.uuid4())[:8]
        download_path = f"downloads/{video_id}.mp4"

        print(f"📥 Downloading video: {req.url}")

        ydl_opts = {
            'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
            'outtmpl': download_path,
            'quiet': False,
            'no_warnings': False,
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([req.url])

        print(f"✅ Video downloaded successfully.")
        
        process_with_ffmpeg(download_path, video_id)

        return {
            "status": "success",
            "video_url": f"http://localhost:8000/outputs/{video_id}_short.mp4"
        }

    except Exception as e:
        print(f"❌ Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/upload")
async def upload_video(file: UploadFile = File(...)):
    try:
        video_id = str(uuid.uuid4())[:8]
        save_path = f"downloads/{video_id}.mp4"

        print(f"📤 Receiving upload: {file.filename}")

        with open(save_path, "wb") as f:
            content = await file.read()
            f.write(content)

        print(f"✅ File saved. Processing...")
        
        process_with_ffmpeg(save_path, video_id)

        return {
            "status": "success",
            "video_url": f"http://localhost:8000/outputs/{video_id}_short.mp4"
        }

    except Exception as e:
        print(f"❌ Upload error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
def health_check():
    ffmpeg_ok = shutil.which("ffmpeg") is not None
    return {
        "status": "ok",
        "ffmpeg": "found" if ffmpeg_ok else "NOT FOUND - please install",
    }

# Serve processed videos statically
app.mount("/outputs", StaticFiles(directory="public/outputs"), name="outputs")

if __name__ == "__main__":
    import uvicorn
    print("🚀 KortShort Backend starting...")
    print(f"📁 FFmpeg: {shutil.which('ffmpeg') or 'NOT FOUND!'}")
    uvicorn.run(app, host="0.0.0.0", port=8000)
