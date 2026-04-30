import os
import subprocess
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import yt_dlp
import uuid

app = FastAPI()

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

@app.post("/process")
def process_video(req: VideoRequest):
    try:
        video_id = str(uuid.uuid4())[:8]
        download_path = f"downloads/{video_id}.mp4"
        output_path = f"public/outputs/{video_id}_short.mp4"
        
        os.makedirs("downloads", exist_ok=True)
        os.makedirs("public/outputs", exist_ok=True)

        print(f"📥 Baixando video: {req.url}")
        
        # Configure yt-dlp to download the best quality mp4
        ydl_opts = {
            'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
            'outtmpl': download_path,
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([req.url])

        print(f"✅ Vídeo baixado. Iniciando corte e crop (9:16) com FFmpeg...")
        
        # FFmpeg command to crop to 9:16 vertical video and take the first 15 seconds (for MVP)
        # crop=ih*9/16:ih forces a 9:16 aspect ratio based on height
        ffmpeg_cmd = [
            "ffmpeg", "-y", "-i", download_path, 
            "-t", "15", 
            "-vf", "crop=ih*9/16:ih", 
            "-c:a", "aac", 
            "-c:v", "libx264", 
            "-preset", "fast",
            output_path
        ]
        
        subprocess.run(ffmpeg_cmd, check=True)
        
        print(f"🎬 Processamento concluído: {output_path}")
        
        return {"status": "success", "video_url": f"http://localhost:8000/outputs/{video_id}_short.mp4"}

    except Exception as e:
        print(f"❌ Erro: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Servir os vídeos processados estaticamente
from fastapi.staticfiles import StaticFiles
app.mount("/outputs", StaticFiles(directory="public/outputs"), name="outputs")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
