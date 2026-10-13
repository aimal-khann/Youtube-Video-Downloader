# 🚀 TubeFlow — Cloud Pro YouTube Video & Audio Downloader

A clean, modern, and high-performance YouTube downloader web application. Download videos in up to **4K Ultra HD** or extract crisp **Studio 320 kbps MP3** audio directly in your browser. Built with **FastAPI**, **yt-dlp**, and **FFmpeg**, and fully configured for **1-click deployment on Railway**.

---

## ✨ Features & Highlights

### 🎨 Ultra-Professional Cloud UI
- **Modern Tech Aesthetic**: Sleek obsidian-slate theme with subtle ambient glow and high-contrast typography.
- **Light & Dark Mode**: One-click theme switcher in the header with persistent local preferences.
- **Zero Modals or Popups**: All controls and download progress happen seamlessly in-place inside the card.
- **Private & Stateless**: No tracking, no public download history, and automatic temporary file purging on the server.

### 🎥 Simple 2-Option Format & Quality Dropdown
- **Format Toggle**:
  - **Video (with Audio)**: High-definition video merged with crisp audio track via FFmpeg.
  - **Audio Only (MP3)**: Studio 320kbps MP3 or lossless M4A audio with album cover art.
- **Quality Dropdown**: All resolutions (4K, 1440p, 1080p, 720p, 480p, 360p) and audio bitrates (320k, 256k, 128k, etc.) with estimated file sizes and recommended presets pre-selected.
- **Direct Download**: Single prominent download button directly beneath the dropdown.

### ⚡ Seamless In-Place Live Progress & Direct Browser Downloads
- **Inline Progress Tracker**: Real-time progress bar with live percentage, download speed (MB/s), ETA countdown, and downloaded size counters directly inside the card.
- **Automatic Browser Download**: Seamlessly triggers standard browser download to the user's downloads folder upon completion.
- **Convert Another Video**: Instant 1-click button to reset and convert a new link.

---

## ☁️ How to Deploy to Railway

The project is pre-configured with `nixpacks.toml`, `Procfile`, and `Dockerfile` for seamless deployment on [Railway.app](https://railway.app).

### Step 1: Push your project to GitHub
```bash
git init
git add .
git commit -m "TubeFlow Cloud Pro"
git branch -M main
git remote add origin https://github.com/<your-username>/<your-repo-name>.git
git push -u origin main
```

### Step 2: Deploy on Railway
1. Go to [Railway.app](https://railway.app) and sign in.
2. Click **"New Project"** -> **"Deploy from GitHub repo"**.
3. Select your repository.
4. Railway will automatically detect `nixpacks.toml` and install:
   - **Python 3.11**
   - **FFmpeg**
   - **Node.js**
5. Go to **Settings** -> **Networking** -> click **"Generate Domain"** to get your public HTTPS URL (e.g. `https://tubeflow-production.up.railway.app`).
6. Your downloader is live on the internet! 🚀

---

## 💻 How to Run Locally

### Option 1: One-Click Batch Launcher (Windows)
Double-click:
```bat
run.bat
```

### Option 2: Command Line
From the project folder, run:
```powershell
python main.py
```
This automatically verifies FFmpeg, binds to an available port (`http://127.0.0.1:8000`), and opens your default browser.

---

## 🛠️ Project Structure

```
e:\Youtube Downloader\
├── backend\
│   ├── app.py             # FastAPI backend with REST endpoints & background cleanup
│   ├── downloader.py      # yt-dlp downloader engine with FFmpeg integration
│   └── ffmpeg_finder.py   # Automatic detector for system, Linux, or Winget FFmpeg
├── frontend\
│   ├── index.html         # Modern semantic HTML5 interface
│   ├── styles.css         # Modern stylesheet with dark/light mode tokens
│   └── app.js             # Reactive client logic & inline progress polling
├── downloads\             # Ephemeral download cache (auto-cleaned every 30 mins)
├── nixpacks.toml          # Railway configuration (Python, FFmpeg, Node.js)
├── Procfile               # Railway process launcher
├── Dockerfile             # Production container fallback
├── requirements.txt       # Python dependencies
├── run.bat                # Windows 1-click launcher
├── main.py                # Standalone entry point (auto-detects local vs cloud PORT)
└── README.md              # Documentation
```
