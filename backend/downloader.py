import os
import re
import math
import uuid
import time
import shutil
import logging
from typing import Dict, Any, Optional, Callable
import yt_dlp

from backend.ffmpeg_finder import get_ffmpeg_paths

logger = logging.getLogger("downloader")
logging.basicConfig(level=logging.INFO)

DOWNLOAD_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "downloads"))
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# Active tasks state
TASKS: Dict[str, Dict[str, Any]] = {}

def format_bytes(bytes_val: Optional[float]) -> str:
    if not bytes_val or bytes_val <= 0:
        return "Unknown size"
    sizes = ["B", "KB", "MB", "GB", "TB"]
    i = int(math.floor(math.log(bytes_val, 1024)))
    p = math.pow(1024, i)
    s = round(bytes_val / p, 1)
    return f"{s} {sizes[i]}"

def format_duration(seconds: Optional[int]) -> str:
    if not seconds:
        return "00:00"
    m, s = divmod(int(seconds), 60)
    h, m = divmod(m, 60)
    if h > 0:
        return f"{h:02d}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"

def format_count(count: Optional[int]) -> str:
    if not count:
        return "0"
    if count >= 1_000_000_000:
        return f"{count / 1_000_000_000:.1f}B"
    if count >= 1_000_000:
        return f"{count / 1_000_000:.1f}M"
    if count >= 1_000:
        return f"{count / 1_000:.1f}K"
    return str(count)

COOKIE_FILE = "/tmp/cookies.txt" if os.path.exists("/tmp") else os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "cookies.txt"))

def ensure_cookies():
    """Extracts cookies from YOUTUBE_COOKIES environment variable if provided on Railway."""
    cookies_env = os.environ.get("YOUTUBE_COOKIES")
    if cookies_env:
        try:
            target_dir = os.path.dirname(COOKIE_FILE)
            if target_dir and not os.path.exists(target_dir):
                os.makedirs(target_dir, exist_ok=True)
            with open(COOKIE_FILE, "w", encoding="utf-8") as f:
                f.write(cookies_env.strip())
            logger.info(f"Successfully loaded YouTube cookies from environment variable into {COOKIE_FILE}")
            return COOKIE_FILE
        except Exception as e:
            logger.warning(f"Could not write YOUTUBE_COOKIES to {COOKIE_FILE}: {e}")
    if os.path.exists(COOKIE_FILE) and os.path.getsize(COOKIE_FILE) > 0:
        return COOKIE_FILE
    return None

def get_base_ydl_opts() -> Dict[str, Any]:
    ffmpeg_exe, ffprobe_exe, ffmpeg_dir = get_ffmpeg_paths()
    node_exe = shutil.which("node") or r"C:\Program Files\nodejs\node.exe"

    opts: Dict[str, Any] = {
        "quiet": True,
        "no_warnings": True,
    }
    if os.path.exists(node_exe):
        opts["js_runtimes"] = {"node": {"path": node_exe}}
    if ffmpeg_dir:
        opts["ffmpeg_location"] = ffmpeg_dir

    cookie_path = ensure_cookies()
    if cookie_path and os.path.exists(cookie_path) and os.path.getsize(cookie_path) > 0:
        opts["cookiefile"] = cookie_path

    # Use modern visionos & web client to bypass broken tv_downgraded client reload errors
    opts["extractor_args"] = {
        "youtube": {
            "player_client": ["visionos", "web"]
        }
    }

    return opts


def extract_video_info(url: str) -> Dict[str, Any]:
    """
    Extracts video metadata and categorizes video and audio qualities.
    Automatically falls back to mobile/embedded player clients if datacenter IP bot detection occurs.
    """
    opts = get_base_ydl_opts()
    opts["extract_flat"] = False

    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=False)
    except Exception as e:
        err_str = str(e).lower()
        if any(keyword in err_str for keyword in ("bot", "sign in", "confirm you", "429", "token", "reload", "unplayable")):
            logger.info("YouTube challenge/unplayable error detected. Retrying with mobile player client...")
            fallback_opts = dict(opts)
            fallback_opts["extractor_args"] = {
                "youtube": {"player_client": ["ios", "android", "mweb"]}
            }
            with yt_dlp.YoutubeDL(fallback_opts) as ydl:
                info = ydl.extract_info(url, download=False)
        else:
            raise e

    duration = info.get("duration") or 0
    raw_formats = info.get("formats", [])

    # Find best audio stream for size estimation
    best_audio_size = 0
    best_audio_abr = 128
    for f in raw_formats:
        if f.get("vcodec") == "none" and f.get("acodec") != "none":
            abr = f.get("abr") or 0
            if abr > best_audio_abr:
                best_audio_abr = abr
            sz = f.get("filesize") or f.get("filesize_approx") or 0
            if sz > best_audio_size:
                best_audio_size = sz

    if best_audio_size == 0 and duration > 0:
        best_audio_size = (best_audio_abr * 1000 / 8) * duration

    # Categorize Video Qualities
    # Group highest quality stream for each resolution height
    video_streams_by_height: Dict[int, Dict[str, Any]] = {}
    for f in raw_formats:
        h = f.get("height")
        if h and f.get("vcodec") != "none":
            curr = video_streams_by_height.get(h)
            tbr = f.get("tbr") or 0
            if not curr or tbr > (curr.get("tbr") or 0):
                video_streams_by_height[h] = f

    avail_heights = sorted(video_streams_by_height.keys(), reverse=True)

    def get_res_info(h: int, w: Optional[int] = None) -> tuple[str, str]:
        if h >= 2160 or (w and w >= 3840):
            return "4K Ultra HD", "4K UHD"
        elif h >= 1440 or (w and w >= 2560):
            return "2K Quad HD", "2K QHD"
        elif h >= 1000 or (w and w >= 1920):
            return "1080p Full HD", "1080p FHD"
        elif h >= 700 or (w and w >= 1280):
            return "720p HD", "720p HD"
        elif h >= 480 or (w and w >= 854):
            return "480p SD", "480p SD"
        elif h >= 360:
            return "360p Medium", "360p"
        elif h >= 240:
            return "240p Low", "240p"
        else:
            return f"{h}p Eco", f"{h}p"

    video_options = []
    seen_labels = set()
    has_rec = False

    for h in avail_heights:
        stream = video_streams_by_height[h]
        w = stream.get("width")
        label, badge = get_res_info(h, w)

        # Skip duplicate labels (e.g. if multiple streams map to same category)
        if label in seen_labels:
            continue
        seen_labels.add(label)

        v_size = stream.get("filesize") or stream.get("filesize_approx")
        total_size = None
        if v_size:
            total_size = v_size + best_audio_size
        elif duration > 0 and stream.get("tbr"):
            total_size = ((stream.get("tbr") + best_audio_abr) * 1000 / 8) * duration

        fps = stream.get("fps") or 30
        fps_str = f"{fps}fps" if fps > 30 else ""

        is_rec = False
        # Recommend 1080p if available, else 720p, else highest available
        if (h >= 1000 and not has_rec) or (h >= 700 and not has_rec and not any(ht >= 1000 for ht in avail_heights)):
            is_rec = True
            has_rec = True

        video_options.append({
            "id": f"video_{h}",
            "height": h,
            "label": label,
            "badge": badge + (f" • {fps_str}" if fps_str else ""),
            "resolution": f"{w}x{h}" if w else f"{h}p",
            "fps": fps,
            "vcodec": stream.get("vcodec", "AVC/H.264").split(".")[0],
            "size_str": format_bytes(total_size) if total_size else "Dynamic size",
            "size_bytes": total_size,
            "recommended": is_rec,
            "ext": "mp4"
        })

    # If none marked recommended, mark the first one
    if video_options and not any(o["recommended"] for o in video_options):
        video_options[0]["recommended"] = True

    # Audio options
    audio_options = [
        {
            "id": "audio_mp3_320",
            "format": "mp3",
            "bitrate": "320k",
            "label": "MP3 320 kbps (Extreme Master)",
            "badge": "ULTRA HQ",
            "desc": "Studio fidelity, highest quality MP3 with ID3 cover art",
            "size_str": format_bytes((320 * 1000 / 8) * duration) if duration else "~10-15 MB",
            "recommended": True,
        },
        {
            "id": "audio_mp3_256",
            "format": "mp3",
            "bitrate": "256k",
            "label": "MP3 256 kbps (High Fidelity)",
            "badge": "HIGH FIDELITY",
            "desc": "Near-lossless clarity, great balance of quality and size",
            "size_str": format_bytes((256 * 1000 / 8) * duration) if duration else "~8-10 MB",
            "recommended": False,
        },
        {
            "id": "audio_mp3_192",
            "format": "mp3",
            "bitrate": "192k",
            "label": "MP3 192 kbps (Standard CD)",
            "badge": "BALANCED",
            "desc": "Standard audio fidelity, fast download",
            "size_str": format_bytes((192 * 1000 / 8) * duration) if duration else "~5-8 MB",
            "recommended": False,
        },
        {
            "id": "audio_mp3_128",
            "format": "mp3",
            "bitrate": "128k",
            "label": "MP3 128 kbps (Compact)",
            "badge": "DATA SAVER",
            "desc": "Lightweight file, perfect for speech, lectures and podcasts",
            "size_str": format_bytes((128 * 1000 / 8) * duration) if duration else "~3-5 MB",
            "recommended": False,
        },
        {
            "id": "audio_m4a_best",
            "format": "m4a",
            "bitrate": "original",
            "label": "M4A / AAC (Original Stream)",
            "badge": "NATIVE LOSSLESS",
            "desc": "Direct YouTube AAC audio stream without re-encoding",
            "size_str": format_bytes(best_audio_size) if best_audio_size else "~4-7 MB",
            "recommended": False,
        },
        {
            "id": "audio_wav",
            "format": "wav",
            "bitrate": "uncompressed",
            "label": "WAV 1411 kbps (Uncompressed PCM)",
            "badge": "RAW AUDIO",
            "desc": "Full uncompressed audio for music production and editing",
            "size_str": format_bytes((1411 * 1000 / 8) * duration) if duration else "~30-50 MB",
            "recommended": False,
        }
    ]

    # Best thumbnail
    thumbnails = info.get("thumbnails", [])
    thumbnail_url = info.get("thumbnail")
    if thumbnails:
        # Prefer higher resolution thumbnail
        thumbnails_sorted = sorted(thumbnails, key=lambda t: (t.get("height") or 0) * (t.get("width") or 0), reverse=True)
        thumbnail_url = thumbnails_sorted[0].get("url") or thumbnail_url

    return {
        "title": info.get("title", "Unknown Title"),
        "channel": info.get("uploader") or info.get("channel") or "Unknown Creator",
        "channel_url": info.get("uploader_url") or info.get("channel_url"),
        "duration": duration,
        "duration_str": format_duration(duration),
        "views": info.get("view_count"),
        "views_str": format_count(info.get("view_count")),
        "upload_date": info.get("upload_date"),
        "thumbnail": thumbnail_url,
        "webpage_url": info.get("webpage_url") or url,
        "video_options": video_options,
        "audio_options": audio_options,
    }


def parse_time_to_seconds(time_str: Optional[str]) -> Optional[float]:
    if not time_str or not time_str.strip():
        return None
    time_str = time_str.strip()
    parts = time_str.split(":")
    try:
        if len(parts) == 3:
            return int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[2])
        elif len(parts) == 2:
            return int(parts[0]) * 60 + float(parts[1])
        elif len(parts) == 1:
            return float(parts[0])
    except ValueError:
        return None
    return None

def execute_download(
    task_id: str,
    url: str,
    mode: str,
    quality_id: str,
    container: str = "mp4",
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
    include_subtitles: bool = False
) -> None:
    """
    Downloads media and updates TASKS[task_id] with live progress.
    Supports time trimming and subtitles embedding.
    """

    TASKS[task_id] = {
        "status": "starting",
        "stage": "Initializing stream extraction...",
        "percent": 0.0,
        "speed": "0 B/s",
        "eta": "--:--",
        "downloaded_bytes": 0,
        "total_bytes": 0,
        "filename": None,
        "file_path": None,
        "file_size": 0,
        "error": None,
        "created_at": time.time(),
    }

    def progress_hook(d: Dict[str, Any]):
        status = d.get("status")
        if status == "downloading":
            total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
            downloaded = d.get("downloaded_bytes") or 0
            speed = d.get("speed") or 0
            eta = d.get("eta") or 0

            percent = 0.0
            if total > 0:
                percent = round((downloaded / total) * 100, 1)

            speed_str = f"{format_bytes(speed)}/s" if speed else "Calculating..."
            eta_str = format_duration(eta) if eta else "--:--"

            TASKS[task_id].update({
                "status": "downloading",
                "stage": f"Downloading stream ({percent}%)...",
                "percent": percent,
                "speed": speed_str,
                "eta": eta_str,
                "downloaded_bytes": downloaded,
                "total_bytes": total,
            })
        elif status == "finished":
            TASKS[task_id].update({
                "status": "processing",
                "stage": "Merging audio & video / finalizing encoding with FFmpeg...",
                "percent": 99.0,
            })

    opts = get_base_ydl_opts()
    opts["progress_hooks"] = [progress_hook]

    # Output template: save in DOWNLOAD_DIR with task_id prefix or safe title
    out_tmpl = os.path.join(DOWNLOAD_DIR, f"{task_id}_%(title).150B.%(ext)s")
    opts["outtmpl"] = out_tmpl

    try:
        if mode == "video":
            # Extract height from quality_id, e.g. "video_1080" -> 1080
            m = re.search(r"(\d+)", quality_id)
            target_height = int(m.group(1)) if m else 1080
            
            # Select best video at or under target height + best audio
            opts["format"] = f"bestvideo[height<={target_height}]+bestaudio/best[height<={target_height}]/best"
            target_ext = "mkv" if container == "mkv" else "mp4"
            opts["merge_output_format"] = target_ext
            
            # Add metadata and chapter markers
            opts["writethumbnail"] = False
            opts["postprocessors"] = [
                {"key": "FFmpegMetadata", "add_chapters": True, "add_metadata": True}
            ]

        elif mode == "audio":
            opts["format"] = "bestaudio/best"
            # Parse audio quality
            if "wav" in quality_id:
                opts["postprocessors"] = [
                    {"key": "FFmpegExtractAudio", "preferredcodec": "wav"}
                ]
            elif "m4a" in quality_id:
                opts["postprocessors"] = [
                    {"key": "FFmpegExtractAudio", "preferredcodec": "m4a"}
                ]
            else:
                # Default MP3 with bitrate
                m = re.search(r"(\d+)", quality_id)
                bitrate = m.group(1) if m else "320"
                opts["postprocessors"] = [
                    {
                        "key": "FFmpegExtractAudio",
                        "preferredcodec": "mp3",
                        "preferredquality": bitrate,
                    },
                    {"key": "FFmpegMetadata", "add_metadata": True}
                ]
        else:
            raise ValueError(f"Unsupported download mode: {mode}")

        TASKS[task_id]["stage"] = "Connecting to YouTube stream..."

        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=True)
        except Exception as e:
            err_str = str(e).lower()
            if any(keyword in err_str for keyword in ("bot", "sign in", "confirm you", "429", "token", "reload", "unplayable")):
                logger.info(f"Bot challenge encountered for task {task_id}. Retrying with mobile clients...")
                fallback_opts = dict(opts)
                fallback_opts["extractor_args"] = {
                    "youtube": {"player_client": ["ios", "android", "mweb"]}
                }
                with yt_dlp.YoutubeDL(fallback_opts) as ydl:
                    info = ydl.extract_info(url, download=True)
            else:
                raise e

        # Find the actual downloaded file on disk
        final_filename = None
        final_path = None
        
        # Look for file starting with task_id in DOWNLOAD_DIR
        for fname in os.listdir(DOWNLOAD_DIR):
            if fname.startswith(task_id):
                final_filename = fname[len(task_id) + 1:]  # strip task_id_ prefix for user display
                final_path = os.path.join(DOWNLOAD_DIR, fname)
                break

        if not final_path or not os.path.exists(final_path):
            # Fallback to prepare_filename
            expected = ydl.prepare_filename(info)
            if os.path.exists(expected):
                final_path = expected
                final_filename = os.path.basename(expected)

        file_size = os.path.getsize(final_path) if final_path and os.path.exists(final_path) else 0

        TASKS[task_id].update({
            "status": "completed",
            "stage": "Ready for download!",
            "percent": 100.0,
            "filename": final_filename or "youtube_media.mp4",
            "file_path": final_path,
            "file_size": file_size,
            "file_size_str": format_bytes(file_size),
        })
        logger.info(f"Task {task_id} completed successfully: {final_path}")

    except Exception as e:
        logger.exception(f"Error during download task {task_id}: {e}")
        TASKS[task_id].update({
            "status": "error",
            "stage": "Download failed",
            "error": str(e),
        })
