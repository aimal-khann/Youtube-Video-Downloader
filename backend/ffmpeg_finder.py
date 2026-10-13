import os
import shutil
import sys

def get_ffmpeg_paths():
    """
    Locates ffmpeg.exe and ffprobe.exe on the system.
    Checks:
    1. System PATH
    2. Winget Gyan.FFmpeg installation directory
    3. imageio-ffmpeg package binaries
    Returns (ffmpeg_exe, ffprobe_exe, ffmpeg_dir)
    """
    ffmpeg_exe = shutil.which("ffmpeg")
    ffprobe_exe = shutil.which("ffprobe")
    
    # Check winget directory if not in PATH
    winget_dir = r"C:\Users\menal\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-9.0.2-full_build\bin"
    if os.path.exists(winget_dir):
        if not ffmpeg_exe and os.path.exists(os.path.join(winget_dir, "ffmpeg.exe")):
            ffmpeg_exe = os.path.join(winget_dir, "ffmpeg.exe")
        if not ffprobe_exe and os.path.exists(os.path.join(winget_dir, "ffprobe.exe")):
            ffprobe_exe = os.path.join(winget_dir, "ffprobe.exe")
        # Ensure it is in os.environ['PATH']
        if winget_dir not in os.environ.get("PATH", ""):
            os.environ["PATH"] = winget_dir + os.pathsep + os.environ.get("PATH", "")

    # Check imageio_ffmpeg as fallback for ffmpeg
    if not ffmpeg_exe:
        try:
            import imageio_ffmpeg
            img_exe = imageio_ffmpeg.get_ffmpeg_exe()
            if os.path.exists(img_exe):
                ffmpeg_exe = img_exe
        except Exception:
            pass

    ffmpeg_dir = os.path.dirname(ffmpeg_exe) if ffmpeg_exe else None
    return ffmpeg_exe, ffprobe_exe, ffmpeg_dir

if __name__ == "__main__":
    f_exe, p_exe, f_dir = get_ffmpeg_paths()
    print("FFmpeg:", f_exe)
    print("FFprobe:", p_exe)
    print("Directory:", f_dir)
