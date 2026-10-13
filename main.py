import os
import sys
import socket
import webbrowser
import threading
import time

# Ensure safe console encoding on Windows to prevent cp1252 UnicodeEncodeError
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import uvicorn
from backend.ffmpeg_finder import get_ffmpeg_paths

def get_free_port(preferred_port: int = 8000, max_tries: int = 20) -> int:
    """Finds an available local port starting from preferred_port."""
    for port in range(preferred_port, preferred_port + max_tries):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("127.0.0.1", port))
                return port
            except OSError:
                continue
    return preferred_port

def main():
    print("=" * 65)
    print("  [*] TubeFlow - Fast & Simple YouTube Downloader")
    print("=" * 65)
    
    ffmpeg_exe, ffprobe_exe, ffmpeg_dir = get_ffmpeg_paths()
    if ffmpeg_exe:
        print(f"  [+] FFmpeg Engine: {ffmpeg_exe}")
    else:
        print("  [!] Warning: FFmpeg not detected. Some muxing features may be limited.")
    
    downloads_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "downloads"))
    os.makedirs(downloads_path, exist_ok=True)
    print(f"  [+] Downloads Folder: {downloads_path}")
    
    # Check if running in cloud (Railway, Render, Heroku)
    env_port = os.environ.get("PORT")
    is_cloud = bool(env_port or os.environ.get("RAILWAY_ENVIRONMENT"))

    if env_port:
        port = int(env_port)
        host = "0.0.0.0"
    else:
        port = get_free_port(8000)
        host = "127.0.0.1"

    web_url = f"http://{host}:{port}"
    print(f"  [+] Web Interface: {web_url}")
    print("=" * 65)
    print("  Starting server... Press Ctrl+C to stop.")

    # Automatically open browser only when running locally on Windows/Desktop
    if not is_cloud:
        def open_browser():
            time.sleep(1.2)
            try:
                webbrowser.open(f"http://127.0.0.1:{port}")
            except Exception:
                pass

        threading.Thread(target=open_browser, daemon=True).start()

    uvicorn.run("backend.app:app", host=host, port=port, log_level="info")

if __name__ == "__main__":
    main()
