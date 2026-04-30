# -*- coding: utf-8 -*-
"""
KortShort AI Module
- Whisper: transcription + word-level timestamps for animated captions
- Ollama/Qwen: intelligent viral moment curation
- OpenCV: face-tracking smart reframe
"""

import os
import json
import subprocess
import requests
import cv2
import numpy as np

# ===== WHISPER TRANSCRIPTION =====
_whisper_model = None

def get_whisper_model(model_size="base"):
    """Lazy-load Whisper model (loads once, reuses)."""
    global _whisper_model
    if _whisper_model is None:
        import whisper
        print(f"[AI] Loading Whisper model: {model_size}")
        _whisper_model = whisper.load_model(model_size)
        print("[AI] Whisper model loaded.")
    return _whisper_model

def transcribe_video(video_path: str, model_size="base") -> dict:
    """Transcribe video with word-level timestamps."""
    model = get_whisper_model(model_size)
    print(f"[AI] Transcribing: {video_path}")
    result = model.transcribe(video_path, word_timestamps=True, language=None)
    return result

def generate_ass_subtitles(transcription: dict, output_path: str,
                           font_size=18, primary_color="&H00FFFFFF",
                           highlight_color="&H0000FFFF"):
    """Generate .ass subtitle file with word-by-word karaoke highlighting."""
    header = f"""[Script Info]
Title: KortShort Captions
ScriptType: v4.00+
WrapStyle: 0
PlayResX: 1080
PlayResY: 1920

[V4+ Styles]
Format: Name,Fontname,Fontsize,PrimaryColour,SecondaryColour,OutlineColour,BackColour,Bold,Italic,Underline,StrikeOut,ScaleX,ScaleY,Spacing,Angle,BorderStyle,Outline,Shadow,Alignment,MarginL,MarginR,MarginV,Encoding
Style: Default,Inter,{font_size},{primary_color},&H000000FF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,2,1,2,40,40,80,1
Style: Highlight,Inter,{font_size},{highlight_color},&H000000FF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,3,1,2,40,40,80,1

[Events]
Format: Layer,Start,End,Style,Name,MarginL,MarginR,MarginV,Effect,Text
"""
    events = []

    for segment in transcription.get("segments", []):
        words = segment.get("words", [])
        if not words:
            continue

        seg_start = format_ass_time(segment["start"])
        seg_end = format_ass_time(segment["end"])

        # Build karaoke line: each word gets highlight timing
        karaoke_parts = []
        for w in words:
            duration_cs = int((w["end"] - w["start"]) * 100)  # centiseconds
            word_text = w["word"].strip()
            if word_text:
                karaoke_parts.append(f"{{\\kf{duration_cs}}}{word_text}")

        line_text = " ".join(karaoke_parts) if karaoke_parts else segment.get("text", "").strip()
        events.append(f"Dialogue: 0,{seg_start},{seg_end},Highlight,,0,0,0,,{line_text}")

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(header)
        f.write("\n".join(events))

    return output_path

def format_ass_time(seconds: float) -> str:
    """Convert seconds to ASS time format H:MM:SS.CC"""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    cs = int((seconds % 1) * 100)
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"


# ===== OLLAMA/QWEN CURATION =====

def find_viral_moments(transcript_text: str, duration: float,
                       model="qwen3.5:9b", max_clips=4) -> list:
    """Use local LLM to identify the best viral moments from transcription."""
    prompt = f"""You are an expert video editor for TikTok and Instagram Reels.
Analyze this video transcription and identify the {max_clips} best segments for viral short clips.

For each segment, consider:
- Strong hooks that grab attention in the first 2 seconds
- Emotional peaks, surprising statements, or funny moments
- Punchlines, key insights, or quotable phrases
- High-energy or dramatic moments

Video duration: {duration:.0f} seconds

Transcription:
{transcript_text[:3000]}

Return ONLY a valid JSON array with this exact format (no markdown, no explanation):
[
  {{"start": 12.5, "duration": 30, "reason": "Strong hook about..."}},
  {{"start": 95.0, "duration": 25, "reason": "Emotional peak when..."}}
]

Rules:
- start and duration are in seconds
- duration between 15-45 seconds
- segments must not overlap
- return exactly {max_clips} segments
"""

    try:
        print(f"[AI] Asking {model} for viral moments...")
        response = requests.post(
            "http://localhost:11434/api/generate",
            json={"model": model, "prompt": prompt, "stream": False},
            timeout=120
        )

        if response.status_code != 200:
            print(f"[AI] Ollama error: {response.status_code}")
            return []

        raw = response.json().get("response", "")
        # Extract JSON from response (handle markdown wrapping)
        raw = raw.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        raw = raw.strip()

        segments = json.loads(raw)

        # Validate segments
        valid = []
        for seg in segments:
            s = float(seg.get("start", 0))
            d = float(seg.get("duration", 30))
            if s >= 0 and d >= 5 and s + d <= duration + 5:
                valid.append({
                    "start": round(s, 1),
                    "duration": round(min(d, 45), 1),
                    "reason": seg.get("reason", "AI selected")
                })

        print(f"[AI] Found {len(valid)} viral moments")
        return valid[:max_clips]

    except Exception as e:
        print(f"[AI] Curation error: {e}")
        return []


# ===== OPENCV SMART REFRAME =====

def detect_face_positions(video_path: str, sample_interval=10) -> list:
    """Sample frames and detect face center X positions for smart reframing."""
    face_cascade = cv2.CascadeClassifier(
        cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
    )

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        return []

    fps = cap.get(cv2.CAP_PROP_FPS) or 30
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))

    positions = []
    frame_idx = 0

    while frame_idx < total_frames:
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
        ret, frame = cap.read()
        if not ret:
            break

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(gray, scaleFactor=1.3, minNeighbors=5, minSize=(60, 60))

        if len(faces) > 0:
            # Use largest face
            areas = [w * h for (x, y, w, h) in faces]
            largest = faces[areas.index(max(areas))]
            x, y, w, h = largest
            center_x = x + w // 2
            positions.append({"frame": frame_idx, "time": frame_idx / fps, "center_x": center_x})
        else:
            positions.append({"frame": frame_idx, "time": frame_idx / fps, "center_x": width // 2})

        frame_idx += sample_interval

    cap.release()
    return positions

def build_smart_crop_filter(face_positions: list, video_width: int, video_height: int) -> str:
    """Build FFmpeg crop filter string that follows face positions.

    For simplicity, we calculate the average face position and use a static crop
    centered on that position. A more advanced version could use keyframes.
    """
    if not face_positions:
        return "crop=ih*9/16:ih"  # fallback: center crop

    # Calculate weighted average center (more weight to frames with faces)
    centers = [p["center_x"] for p in face_positions]
    avg_center = int(np.mean(centers))

    # Calculate crop dimensions
    crop_w = int(video_height * 9 / 16)
    crop_h = video_height

    # Clamp crop position to video bounds
    crop_x = max(0, min(avg_center - crop_w // 2, video_width - crop_w))

    return f"crop={crop_w}:{crop_h}:{crop_x}:0"


def get_video_dimensions(video_path: str) -> tuple:
    """Get video width and height using OpenCV."""
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        return (1920, 1080)
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    cap.release()
    return (w, h)
