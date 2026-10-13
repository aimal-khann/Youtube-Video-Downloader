/**
 * TubeFlow — Cloud Pro YouTube Downloader
 * Client-Side Application Controller: Unified Card, Inline Progress Bar,
 * Direct Browser Download, Zero Clutter, Zero Modal Popups.
 */

// Application State
window.appState = {
  videoData: null,
  activeMode: "video", // "video" or "audio"
  selectedQualityId: null,
  selectedContainer: "mp4", // "mp4" or "mkv"
  currentTaskId: null,
  progressTimer: null,
  theme: localStorage.getItem("tubeflow_theme") || "dark",
};

// Safe DOM helper
function $(id) {
  return document.getElementById(id);
}

// Safe event listener helper
function on(idOrEl, event, handler) {
  const el = typeof idOrEl === "string" ? $(idOrEl) : idOrEl;
  if (el) el.addEventListener(event, handler);
  return el;
}

// Toast Notification Helper
window.showToast = function(message, type = "info") {
  const container = $("toastContainer");
  if (!container) return;

  const toast = document.createElement("div");
  toast.className = `toast ${type}`;
  
  let icon = "ℹ️";
  if (type === "success") icon = "✅";
  if (type === "error") icon = "⚠️";

  toast.innerHTML = `<span>${icon}</span><span>${message}</span>`;
  container.appendChild(toast);

  setTimeout(() => {
    toast.style.opacity = "0";
    toast.style.transform = "translateY(12px)";
    toast.style.transition = "all 0.25s ease";
    setTimeout(() => toast.remove(), 260);
  }, 3500);
};

// Theme Switcher (Dark / Light)
window.toggleAppTheme = function() {
  const state = window.appState;
  state.theme = state.theme === "dark" ? "light" : "dark";
  document.documentElement.setAttribute("data-theme", state.theme);
  localStorage.setItem("tubeflow_theme", state.theme);
  updateThemeIcons();
};

function updateThemeIcons() {
  const state = window.appState;
  const sunIcon = document.querySelector(".theme-icon-sun");
  const moonIcon = document.querySelector(".theme-icon-moon");
  if (!sunIcon || !moonIcon) return;

  if (state.theme === "light") {
    sunIcon.classList.remove("hidden");
    moonIcon.classList.add("hidden");
  } else {
    sunIcon.classList.add("hidden");
    moonIcon.classList.remove("hidden");
  }
}

// Sample Link Quick Loader
window.loadSample = function(url) {
  const input = $("videoUrlInput");
  const clearBtn = $("clearInputBtn");
  if (input) {
    input.value = url;
    if (clearBtn) clearBtn.classList.remove("hidden");
    window.fetchVideoInfo();
  }
};

// Clipboard Paste
window.pasteFromClipboard = async function() {
  const input = $("videoUrlInput");
  const clearBtn = $("clearInputBtn");
  try {
    const text = await navigator.clipboard.readText();
    if (text) {
      if (input) input.value = text.trim();
      if (clearBtn) clearBtn.classList.remove("hidden");
      window.showToast("Link pasted from clipboard", "info");
      window.fetchVideoInfo();
    }
  } catch (e) {
    if (input) input.focus();
    window.showToast("Please allow clipboard access or press Ctrl+V", "info");
  }
};

// Clear Search Input
window.clearUrlInput = function() {
  const input = $("videoUrlInput");
  const clearBtn = $("clearInputBtn");
  if (input) {
    input.value = "";
    input.focus();
  }
  if (clearBtn) clearBtn.classList.add("hidden");
};

// Dismiss Error Banner
window.dismissErrorCard = function() {
  const card = $("errorCard");
  if (card) card.classList.add("hidden");
};

// Format Mode Switcher (Video vs Audio)
window.switchMode = function(mode) {
  const state = window.appState;
  state.activeMode = mode;

  const tabVideo = $("tabVideoMode");
  const tabAudio = $("tabAudioMode");
  const containerWrap = $("containerPickerWrap");
  const label = $("qualityDropdownLabel");
  const icon = $("stripIcon");

  if (mode === "video") {
    if (tabVideo) {
      tabVideo.classList.add("active");
      tabVideo.setAttribute("aria-selected", "true");
    }
    if (tabAudio) {
      tabAudio.classList.remove("active");
      tabAudio.setAttribute("aria-selected", "false");
    }
    if (containerWrap) containerWrap.classList.remove("hidden");
    if (label) label.textContent = "2. Select Video Resolution:";
    if (icon) icon.textContent = "🎬";
  } else {
    if (tabAudio) {
      tabAudio.classList.add("active");
      tabAudio.setAttribute("aria-selected", "true");
    }
    if (tabVideo) {
      tabVideo.classList.remove("active");
      tabVideo.setAttribute("aria-selected", "false");
    }
    if (containerWrap) containerWrap.classList.add("hidden");
    if (label) label.textContent = "2. Select Audio Bitrate / Format:";
    if (icon) icon.textContent = "🎵";
  }

  populateQualityDropdown();
};

// Quality & Container Change Handlers
window.onQualityChange = function(value) {
  window.appState.selectedQualityId = value;
  updateDownloadButtonAndDetails();
};

window.onContainerChange = function(container) {
  window.appState.selectedContainer = container;
  updateDownloadButtonAndDetails();
};

// Reset Downloader Flow
window.resetDownloader = function() {
  const resultSection = $("resultSection");
  const progressBox = $("inlineProgressBox");
  const successBox = $("inlineSuccessBox");
  const input = $("videoUrlInput");
  const clearBtn = $("clearInputBtn");
  const downloadBtn = $("startDownloadBtn");

  if (progressBox) progressBox.classList.add("hidden");
  if (successBox) successBox.classList.add("hidden");
  if (resultSection) resultSection.classList.add("hidden");
  if (downloadBtn) downloadBtn.disabled = false;

  if (input) {
    input.value = "";
    input.focus();
  }
  if (clearBtn) clearBtn.classList.add("hidden");

  window.appState.videoData = null;
  window.appState.currentTaskId = null;
  if (window.appState.progressTimer) {
    clearInterval(window.appState.progressTimer);
    window.appState.progressTimer = null;
  }
};

// Main Analysis Endpoint
window.fetchVideoInfo = async function() {
  const input = $("videoUrlInput");
  const fetchBtn = $("fetchVideoBtn");
  const spinner = $("fetchSpinner");
  const errorCard = $("errorCard");
  const resultSection = $("resultSection");
  const progressBox = $("inlineProgressBox");
  const successBox = $("inlineSuccessBox");

  if (!input) return;
  const url = input.value.trim();

  if (!url) {
    window.showToast("Please paste a valid YouTube URL first", "error");
    input.focus();
    return;
  }

  if (fetchBtn) fetchBtn.disabled = true;
  if (spinner) spinner.classList.remove("hidden");
  if (errorCard) errorCard.classList.add("hidden");
  if (progressBox) progressBox.classList.add("hidden");
  if (successBox) successBox.classList.add("hidden");

  try {
    const res = await fetch(`/api/info?url=${encodeURIComponent(url)}`);
    const data = await res.json();

    if (!res.ok) {
      throw new Error(data.detail || "Failed to retrieve video details");
    }

    window.appState.videoData = data;
    renderVideoHeader(data);

    // Default to video mode
    window.switchMode("video");

    if (resultSection) {
      resultSection.classList.remove("hidden");
      resultSection.scrollIntoView({ behavior: "smooth", block: "start" });
    }
    window.showToast("Video loaded successfully!", "success");

  } catch (err) {
    console.error("fetchVideoInfo error:", err);
    const titleEl = $("errorTitle");
    const msgEl = $("errorMsg");
    if (titleEl) titleEl.textContent = "Unable to process video";
    if (msgEl) msgEl.textContent = err.message || "Failed to process YouTube link.";
    if (errorCard) errorCard.classList.remove("hidden");
    if (resultSection) resultSection.classList.add("hidden");
    window.showToast(err.message, "error");
  } finally {
    if (fetchBtn) fetchBtn.disabled = false;
    if (spinner) spinner.classList.add("hidden");
  }
};

// Render Video Header Preview
function renderVideoHeader(data) {
  const thumbImg = $("videoThumbImg");
  const durationBadge = $("videoDurationBadge");
  const topQualityBadge = $("videoTopQualityBadge");
  const titleText = $("videoTitleText");
  const channelName = $("videoChannelName");
  const viewsText = $("videoViewsText");
  const durationText = $("videoDurationText");
  const dateText = $("videoDateText");
  const externalLink = $("videoExternalLink");

  if (thumbImg) {
    thumbImg.src = data.thumbnail || "https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?auto=format&fit=crop&w=600&q=80";
  }
  if (durationBadge) durationBadge.textContent = data.duration_str || "00:00";
  
  if (topQualityBadge) {
    if (data.video_options && data.video_options.length > 0) {
      const topBadge = data.video_options[0].badge || "HD";
      topQualityBadge.textContent = topBadge.split("•")[0].trim();
    } else {
      topQualityBadge.textContent = "HD";
    }
  }

  if (titleText) titleText.textContent = data.title || "YouTube Video";
  if (channelName) channelName.textContent = data.channel || "Creator";
  if (viewsText) viewsText.textContent = `${data.views_str || 0} views`;
  if (durationText) durationText.textContent = data.duration_str || "00:00";
  
  if (dateText) {
    if (data.upload_date && data.upload_date.length === 8) {
      const y = data.upload_date.substring(0, 4);
      const m = data.upload_date.substring(4, 6);
      const d = data.upload_date.substring(6, 8);
      dateText.textContent = `${y}-${m}-${d}`;
    } else {
      dateText.textContent = "Available";
    }
  }

  if (externalLink) externalLink.href = data.webpage_url || "#";
}

// Populate Quality Dropdown Dynamically
function populateQualityDropdown() {
  const select = $("qualitySelect");
  if (!select) return;
  select.innerHTML = "";

  const state = window.appState;
  const data = state.videoData;
  if (!data) return;

  if (state.activeMode === "video") {
    const videoOpts = data.video_options || [];
    
    if (videoOpts.length === 0) {
      const optEl = document.createElement("option");
      optEl.value = "best";
      optEl.textContent = "Standard Quality (MP4)";
      select.appendChild(optEl);
      state.selectedQualityId = "best";
    } else {
      const rec = videoOpts.find(o => o.recommended) || videoOpts[0];
      state.selectedQualityId = rec.id;

      videoOpts.forEach((opt) => {
        const optEl = document.createElement("option");
        optEl.value = opt.id;
        
        let recBadge = opt.recommended ? " ★ [Recommended]" : "";
        let sizeInfo = opt.size_str ? ` (~${opt.size_str})` : "";
        let fpsInfo = opt.fps && opt.fps > 30 ? ` • ${opt.fps}fps` : "";
        
        optEl.textContent = `${opt.label}${fpsInfo}${sizeInfo}${recBadge}`;
        if (opt.id === rec.id) optEl.selected = true;

        select.appendChild(optEl);
      });
    }

  } else {
    // Audio Mode
    const audioOpts = data.audio_options || [];

    if (audioOpts.length === 0) {
      const optEl = document.createElement("option");
      optEl.value = "audio_mp3_320";
      optEl.textContent = "MP3 Audio (Highest Quality)";
      select.appendChild(optEl);
      state.selectedQualityId = "audio_mp3_320";
    } else {
      const rec = audioOpts.find(o => o.recommended) || audioOpts[0];
      state.selectedQualityId = rec.id;

      audioOpts.forEach((opt) => {
        const optEl = document.createElement("option");
        optEl.value = opt.id;

        let recBadge = opt.recommended ? " ★ [Recommended]" : "";
        let sizeInfo = opt.size_str ? ` (~${opt.size_str})` : "";
        
        optEl.textContent = `${opt.label}${sizeInfo}${recBadge}`;
        if (opt.id === rec.id) optEl.selected = true;

        select.appendChild(optEl);
      });
    }
  }

  updateDownloadButtonAndDetails();
}

// Update Download Button Label & Strip Notes
function updateDownloadButtonAndDetails() {
  const state = window.appState;
  const data = state.videoData;
  if (!data) return;

  const badgeText = $("selectedBadgeText");
  const btnText = $("downloadBtnText");
  const strip = $("stripDetails");

  if (state.activeMode === "video") {
    const opts = data.video_options || [];
    const current = opts.find(o => o.id === state.selectedQualityId) || opts[0];
    const containerExt = state.selectedContainer.toUpperCase();

    if (current) {
      const badgeClean = current.badge ? current.badge.split("•")[0].trim() : "HD";
      if (badgeText) badgeText.textContent = `${badgeClean} • ${containerExt}`;
      if (btnText) btnText.textContent = `Download ${current.label} (${containerExt})`;
      if (strip) strip.textContent = `Estimated size: ~${current.size_str} • Merged with stereo audio via FFmpeg`;
    } else {
      if (badgeText) badgeText.textContent = `HD • ${containerExt}`;
      if (btnText) btnText.textContent = `Download Video (${containerExt})`;
      if (strip) strip.textContent = `High-definition video with audio stream`;
    }

  } else {
    const opts = data.audio_options || [];
    const current = opts.find(o => o.id === state.selectedQualityId) || opts[0];

    if (current) {
      if (badgeText) badgeText.textContent = `${current.format.toUpperCase()} ${current.bitrate || ''}`;
      if (btnText) btnText.textContent = `Download ${current.format.toUpperCase()} Audio`;
      if (strip) strip.textContent = `${current.desc || ''} • Estimated size: ~${current.size_str}`;
    } else {
      if (badgeText) badgeText.textContent = "MP3 AUDIO";
      if (btnText) btnText.textContent = "Download Audio (MP3)";
      if (strip) strip.textContent = "Extracts highest bitrate audio stream with cover art";
    }
  }
}

// Trigger Download Flow (INLINE LIVE PROGRESS, NO POPUP BOX!)
window.triggerDownload = async function() {
  const state = window.appState;
  const input = $("videoUrlInput");
  const url = state.videoData ? state.videoData.webpage_url : (input ? input.value.trim() : "");
  const downloadBtn = $("startDownloadBtn");

  if (!url) {
    window.showToast("Please enter a valid link first", "error");
    return;
  }

  try {
    if (downloadBtn) downloadBtn.disabled = true;
    showInlineProgress();

    const payload = {
      url: url,
      mode: state.activeMode,
      quality_id: state.selectedQualityId,
      container: state.selectedContainer,
    };

    const res = await fetch("/api/download", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    const data = await res.json();
    if (!res.ok) {
      throw new Error(data.detail || "Could not start download task");
    }

    state.currentTaskId = data.task_id;
    startProgressPolling(data.task_id);

  } catch (err) {
    console.error("triggerDownload error:", err);
    window.showToast(err.message || "Failed to start download", "error");
    if (downloadBtn) downloadBtn.disabled = false;
    hideInlineProgress();
  }
};

function showInlineProgress() {
  const progressBox = $("inlineProgressBox");
  const successBox = $("inlineSuccessBox");
  const statusBadge = $("progressStatusBadge");
  const stageDesc = $("progressStageDesc");
  const fill = $("progressFillBar");
  const pct = $("progressPercentNum");
  const speed = $("statSpeedVal");
  const eta = $("statEtaVal");
  const size = $("statSizeVal");

  if (progressBox) progressBox.classList.remove("hidden");
  if (successBox) successBox.classList.add("hidden");

  if (statusBadge) {
    statusBadge.textContent = "Initializing";
    statusBadge.style.background = "var(--primary-soft)";
    statusBadge.style.color = "var(--primary)";
    statusBadge.style.borderColor = "var(--primary-border)";
  }
  if (stageDesc) stageDesc.textContent = "Connecting to YouTube stream...";
  if (fill) fill.style.width = "0%";
  if (pct) pct.textContent = "0%";
  if (speed) speed.textContent = "0 B/s";
  if (eta) eta.textContent = "--:--";
  if (size) size.textContent = "0 MB";

  // Scroll smoothly to progress
  progressBox?.scrollIntoView({ behavior: "smooth", block: "nearest" });
}

function hideInlineProgress() {
  const progressBox = $("inlineProgressBox");
  if (progressBox) progressBox.classList.add("hidden");
  if (window.appState.progressTimer) {
    clearInterval(window.appState.progressTimer);
    window.appState.progressTimer = null;
  }
}

// Live Progress Polling
function startProgressPolling(taskId) {
  const state = window.appState;
  if (state.progressTimer) clearInterval(state.progressTimer);

  state.progressTimer = setInterval(async () => {
    try {
      const res = await fetch(`/api/progress/${taskId}`);
      if (!res.ok) return;
      const task = await res.json();

      const fill = $("progressFillBar");
      const pct = $("progressPercentNum");
      const statusBadge = $("progressStatusBadge");
      const stageDesc = $("progressStageDesc");
      const speed = $("statSpeedVal");
      const eta = $("statEtaVal");
      const size = $("statSizeVal");

      const percent = task.percent || 0.0;
      if (fill) fill.style.width = `${percent}%`;
      if (pct) pct.textContent = `${percent}%`;
      
      if (statusBadge) statusBadge.textContent = task.status || "Downloading";
      if (stageDesc) stageDesc.textContent = task.stage || "Downloading stream fragments...";

      if (speed) speed.textContent = task.speed || "0 B/s";
      if (eta) eta.textContent = task.eta || "--:--";
      
      if (task.downloaded_bytes && size) {
        const dlMB = (task.downloaded_bytes / (1024 * 1024)).toFixed(1);
        const totalMB = task.total_bytes ? (task.total_bytes / (1024 * 1024)).toFixed(1) : "?";
        size.textContent = `${dlMB} / ${totalMB} MB`;
      }

      // On Download Completion
      if (task.status === "completed") {
        clearInterval(state.progressTimer);
        state.progressTimer = null;

        if (fill) fill.style.width = "100%";
        if (pct) pct.textContent = "100%";
        
        if (statusBadge) {
          statusBadge.textContent = "Completed";
          statusBadge.style.background = "var(--accent-emerald-soft)";
          statusBadge.style.color = "var(--accent-emerald)";
          statusBadge.style.borderColor = "var(--accent-emerald)";
        }

        const fnameText = $("successFilenameText");
        if (fnameText) {
          fnameText.textContent = task.filename ? `Downloaded: ${task.filename}` : "Your file is ready!";
        }

        const saveAgainBtn = $("downloadAgainBtn");
        if (saveAgainBtn) {
          saveAgainBtn.href = `/api/file/${taskId}`;
          saveAgainBtn.setAttribute("download", task.filename || "media");
        }

        const successBox = $("inlineSuccessBox");
        if (successBox) successBox.classList.remove("hidden");

        const downloadBtn = $("startDownloadBtn");
        if (downloadBtn) downloadBtn.disabled = false;

        window.showToast("Download finished successfully!", "success");

        // Automatically trigger browser download
        const autoLink = document.createElement("a");
        autoLink.href = `/api/file/${taskId}`;
        autoLink.download = task.filename || "media";
        document.body.appendChild(autoLink);
        autoLink.click();
        autoLink.remove();
      }

      // On Download Error
      if (task.status === "error") {
        clearInterval(state.progressTimer);
        state.progressTimer = null;

        if (statusBadge) {
          statusBadge.textContent = "Error";
          statusBadge.style.background = "rgba(239, 68, 68, 0.15)";
          statusBadge.style.color = "var(--accent-danger)";
        }
        if (stageDesc) stageDesc.textContent = task.error || "An error occurred during download.";
        
        const downloadBtn = $("startDownloadBtn");
        if (downloadBtn) downloadBtn.disabled = false;

        window.showToast("Download failed: " + (task.error || "Unknown error"), "error");
      }

    } catch (e) {
      console.error("Progress fetch error:", e);
    }
  }, 600);
}

// Health Check
async function checkHealth() {
  const badge = $("engineStatusBadge");
  if (!badge) return;
  try {
    const res = await fetch("/api/health");
    if (res.ok) {
      const data = await res.json();
      if (data.ffmpeg_available) {
        badge.title = "Cloud FFmpeg Engine active";
      } else {
        badge.title = "Basic stream extractor active";
        const dot = badge.querySelector(".indicator-dot");
        if (dot) dot.style.backgroundColor = "#f59e0b";
      }
    }
  } catch (e) {
    console.warn("Backend health check failed:", e);
  }
}

// App Initialization
function initApp() {
  console.log("[TubeFlow Cloud Pro] Initialized successfully.");
  
  // Apply theme
  document.documentElement.setAttribute("data-theme", window.appState.theme);
  updateThemeIcons();

  // URL input keydown Enter
  on("videoUrlInput", "keydown", (e) => {
    if (e.key === "Enter") {
      window.fetchVideoInfo();
    }
  });

  // URL input dynamic clear button
  on("videoUrlInput", "input", () => {
    const input = $("videoUrlInput");
    const clearBtn = $("clearInputBtn");
    if (input && clearBtn) {
      if (input.value.trim().length > 0) {
        clearBtn.classList.remove("hidden");
      } else {
        clearBtn.classList.add("hidden");
      }
    }
  });

  checkHealth();
}

// Safe execution guarantee
if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", initApp);
} else {
  initApp();
}
