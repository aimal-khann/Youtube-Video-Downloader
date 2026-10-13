import os
import uuid
import time
import threading
import subprocess
from typing import Optional
from pydantic import BaseModel

from fastapi import FastAPI, HTTPException, BackgroundTasks, Query
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from backend.downloader import (
    extract_video_info,
    execute_download,
    TASKS,
    DOWNLOAD_DIR,
    format_bytes,
)
from backend.ffmpeg_finder import get_ffmpeg_paths

def cleanup_old_files():
    """Periodically cleans up downloaded files older than 30 minutes to maintain cloud disk space."""
    while True:
        try:
            time.sleep(600)  # Check every 10 minutes
            now = time.time()
            if os.path.exists(DOWNLOAD_DIR):
                for fname in os.listdir(DOWNLOAD_DIR):
                    fpath = os.path.join(DOWNLOAD_DIR, fname)
                    if os.path.isfile(fpath):
                        if now - os.path.getmtime(fpath) > 1800:
                            try:
                                os.remove(fpath)
                            except OSError:
                                pass
            # Clean expired tasks from memory
            old_tids = [tid for tid, t in list(TASKS.items()) if now - t.get("created_at", now) > 1800]
            for tid in old_tids:
                TASKS.pop(tid, None)
        except Exception:
            pass

threading.Thread(target=cleanup_old_files, daemon=True).start()

app = FastAPI(
    title="TubeFlow — YouTube Video & Audio Downloader",
    description="High-performance media extractor with smart quality suggestions and FFmpeg remuxing",
    version="2.0.0",
)

# Enable CORS for local development flexibility
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def add_no_cache_headers(request, call_next):
    response = await call_next(request)
    path = request.url.path
    if path == "/" or path.endswith((".html", ".js", ".css", ".json")):
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
    return response

FRONTEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "frontend"))

class DownloadRequest(BaseModel):
    url: str
    mode: str  # "video" or "audio"
    quality_id: str
    container: Optional[str] = "mp4"

@app.get("/api/health")
def health_check():
    f_exe, p_exe, f_dir = get_ffmpeg_paths()
    return {
        "status": "online",
        "ffmpeg_available": bool(f_exe),
        "ffmpeg_path": f_exe,
        "ffprobe_available": bool(p_exe),
        "downloads_dir": DOWNLOAD_DIR,
    }

@app.get("/api/info")
def get_video_info_endpoint(url: str = Query(..., description="YouTube video or shorts URL")):
    if not url or ("youtube.com" not in url and "youtu.be" not in url):
        raise HTTPException(status_code=400, detail="Please enter a valid YouTube video URL.")
    try:
        data = extract_video_info(url.strip())
        return data
    except Exception as e:
        err_msg = str(e)
        if "Video unavailable" in err_msg:
            detail = "This video is unavailable (it may be private, deleted, or region-restricted)."
        elif "Sign in to confirm" in err_msg or "bot" in err_msg.lower():
            detail = "YouTube bot detection triggered on server IP. Add YOUTUBE_COOKIES to Railway Variables to bypass."
        else:
            detail = f"Unable to fetch video details: {err_msg[:200]}"
        raise HTTPException(status_code=400, detail=detail)

@app.post("/api/download")
def start_download(req: DownloadRequest):
    if not req.url:
        raise HTTPException(status_code=400, detail="Missing video URL")
    if req.mode not in ("video", "audio"):
        raise HTTPException(status_code=400, detail="Invalid mode, must be 'video' or 'audio'")
    
    task_id = str(uuid.uuid4())[:8]

    # Run download in a dedicated background worker thread
    t = threading.Thread(
        target=execute_download,
        args=(task_id, req.url.strip(), req.mode, req.quality_id, req.container or "mp4"),
        daemon=True,
    )
    t.start()

    return {"task_id": task_id, "status": "started"}

@app.get("/api/progress/{task_id}")
def get_progress(task_id: str):
    task = TASKS.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task

@app.get("/api/file/{task_id}")
def download_file(task_id: str):
    task = TASKS.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    if task["status"] != "completed" or not task.get("file_path"):
        raise HTTPException(status_code=400, detail="File is not ready yet")

    file_path = task["file_path"]
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Downloaded file was not found on disk")

    filename = task.get("filename") or os.path.basename(file_path)
    return FileResponse(
        path=file_path,
        filename=filename,
        media_type="application/octet-stream",
    )

@app.post("/api/open-folder/{task_id}")
def open_folder(task_id: str):
    task = TASKS.get(task_id)
    if not task or not task.get("file_path"):
        raise HTTPException(status_code=404, detail="Task or file not found")
    
    file_path = task["file_path"]
    if not os.path.exists(file_path):
        # Open directory if file is gone
        subprocess.run(["explorer", DOWNLOAD_DIR])
        return {"status": "opened_dir"}

    # Windows command to highlight specific file in Explorer
    subprocess.run(["explorer", f"/select,{file_path}"])
    return {"status": "opened_file"}

@app.get("/api/recent-downloads")
def get_recent_downloads():
    results = []
    if os.path.exists(DOWNLOAD_DIR):
        for fname in os.listdir(DOWNLOAD_DIR):
            fpath = os.path.join(DOWNLOAD_DIR, fname)
            if os.path.isfile(fpath):
                stat = os.stat(fpath)
                display_name = fname
                if "_" in fname and len(fname.split("_")[0]) == 8:
                    display_name = fname.split("_", 1)[1]
                
                results.append({
                    "raw_name": fname,
                    "filename": display_name,
                    "size_str": format_bytes(stat.st_size),
                    "modified": stat.st_mtime,
                    "is_video": fname.lower().endswith((".mp4", ".mkv", ".webm")),
                    "is_audio": fname.lower().endswith((".mp3", ".m4a", ".wav", ".aac")),
                })
    results.sort(key=lambda x: x["modified"], reverse=True)
    return results[:15]

# Mount downloads directory
if os.path.exists(DOWNLOAD_DIR):
    app.mount("/downloads", StaticFiles(directory=DOWNLOAD_DIR), name="downloads")

# Mount frontend directory for static assets and index
if os.path.exists(FRONTEND_DIR):
    app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
