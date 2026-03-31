// This is a YouTube information extractor that helps you load video images, titles, and descriptions on YouTube.
import CONFIG from "./config.js";

const BACKEND_BASE_URL = (CONFIG.BASE_URL || "").replace(/\/+$/, "");
const COOKIE_PREF_KEY = "youlaugh_send_cookies";

function isYouTubeVideoUrl(url) {
  try {
    const parsed = new URL(url);
    return (
      parsed.hostname.includes("youtube.com") &&
      (parsed.pathname === "/watch" || parsed.pathname.startsWith("/shorts/"))
    );
  } catch (error) {
    return false;
  }
}

function setBasicUiState({ title, channel, subtitle, thumbnailUrl }) {
  const titleEl = document.querySelector(".video-title");
  const channelEl = document.querySelector(".video-channel");
  const descEl = document.querySelector(".video-desc");
  const thumbDiv = document.querySelector(".thumb");

  titleEl.innerText = title || "No video detected";
  channelEl.innerText = channel || "Open a YouTube video tab";
  descEl.innerText = subtitle || "";

  if (thumbnailUrl) {
    thumbDiv.innerHTML = `<img src="${thumbnailUrl}" alt="Video thumbnail" style="width:100%;height:100%;object-fit:cover;border-radius:inherit;" />`;
  } else {
    thumbDiv.textContent = "img";
  }
}

function triggerClientDownload(downloadUrl, quality) {
  const fallbackOpen = () => window.open(downloadUrl, "_blank");

  if (!chrome.downloads || typeof chrome.downloads.download !== "function") {
    fallbackOpen();
    return;
  }

  chrome.downloads.download(
    {
      url: downloadUrl,
      filename: `youlaugh-${quality}-${Date.now()}.mp4`,
      saveAs: true,
      conflictAction: "uniquify",
    },
    (downloadId) => {
      if (!downloadId || chrome.runtime.lastError) {
        fallbackOpen();
      }
    },
  );
}

function readCookiePreference() {
  return new Promise((resolve) => {
    if (!chrome.storage || !chrome.storage.local) {
      resolve(false);
      return;
    }

    chrome.storage.local.get([COOKIE_PREF_KEY], (result) => {
      if (chrome.runtime.lastError) {
        resolve(false);
        return;
      }

      resolve(Boolean(result[COOKIE_PREF_KEY]));
    });
  });
}

function writeCookiePreference(value) {
  if (!chrome.storage || !chrome.storage.local) return;
  chrome.storage.local.set({ [COOKIE_PREF_KEY]: value });
}

function getCookiesForDomain(domain) {
  return new Promise((resolve) => {
    if (!chrome.cookies || typeof chrome.cookies.getAll !== "function") {
      resolve([]);
      return;
    }

    chrome.cookies.getAll({ domain }, (cookies) => {
      if (chrome.runtime.lastError) {
        console.warn("Cookie read failed:", chrome.runtime.lastError.message);
        resolve([]);
        return;
      }

      resolve(cookies || []);
    });
  });
}

async function collectYouTubeCookies() {
  const domains = [".youtube.com", ".google.com"];
  const results = await Promise.all(domains.map((domain) => getCookiesForDomain(domain)));
  const merged = results.flat();
  const seen = new Set();

  return merged.filter((cookie) => {
    const key = `${cookie.name}|${cookie.domain}|${cookie.path}`;
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });
}

async function fetchFormats(videoUrl, sendCookies) {
  try {
    // This call can be slow because yt-dlp probes the video on the backend.
    const payload = { url: videoUrl };

    if (sendCookies) {
      payload.cookies = await collectYouTubeCookies();
    }

    const res = await fetch(`${BACKEND_BASE_URL}/formats`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(payload),
    });

    const data = await res.json();
    return data.formats || [];
  } catch (err) {
    console.error("Error fetching formats", err);
    return [];
  }
}

function renderFormats(formats) {
  const container = document.getElementById("formats-container");
  container.innerHTML = "";

  formats.forEach((f) => {
    const btn = document.createElement("button");

    btn.className = "format-card";
    btn.innerText = `${f.resolution || "unknown"} - ${f.ext || "?"}`;

    btn.onclick = () => {
      // Client-side download uses the direct URL returned by the backend.
      triggerClientDownload(f.url, f.resolution);
    };

    container.appendChild(btn);
  });
}

function setFormatsStatus(message) {
  const statusEl = document.getElementById("formats-status");
  statusEl.textContent = message || "";
}

function setFormatsLoading(isLoading) {
  const button = document.getElementById("get-formats-btn");
  if (!button) return;

  button.disabled = isLoading;
  button.textContent = isLoading ? "Loading formats..." : "Get Formats";
}

document.addEventListener("DOMContentLoaded", () => {
  const getFormatsBtn = document.getElementById("get-formats-btn");
  const cookieToggle = document.getElementById("send-cookies-toggle");

  // Default UI state before we know the active tab.
  setFormatsLoading(false);
  setFormatsStatus("Open a YouTube video to fetch formats.");
  if (getFormatsBtn) getFormatsBtn.disabled = true;

  if (cookieToggle) {
    readCookiePreference().then((savedValue) => {
      cookieToggle.checked = savedValue;
    });

    cookieToggle.addEventListener("change", () => {
      writeCookiePreference(cookieToggle.checked);
    });
  }

  chrome.tabs.query({ active: true, currentWindow: true }, async (tabs) => {
    const currentTab = tabs && tabs[0];
    const videoUrl = currentTab?.url || "";

    if (!currentTab?.id || !isYouTubeVideoUrl(videoUrl)) {
      setBasicUiState({
        title: "No YouTube watch page",
        channel: "Go to a YouTube video",
        subtitle: "",
      });
      return;
    }

    // Enable the button now that we have a valid YouTube URL.
    if (getFormatsBtn) getFormatsBtn.disabled = false;

    // Fetch formats only when the user clicks, to avoid slow popup load.
    if (getFormatsBtn) {
      getFormatsBtn.addEventListener("click", async () => {
        if (!BACKEND_BASE_URL) {
          setFormatsStatus("Backend URL is missing in config.js");
          return;
        }

        setFormatsLoading(true);
        setFormatsStatus("Fetching formats from backend...");

        const sendCookies = Boolean(cookieToggle && cookieToggle.checked);
        const formats = await fetchFormats(videoUrl, sendCookies);
        renderFormats(formats);

        setFormatsLoading(false);
        setFormatsStatus(
          formats.length
            ? `Found ${formats.length} formats.`
            : "No formats found for this video.",
        );
      });
    }

    // Existing metadata logic stays (title, channel, thumbnail, etc).
    chrome.tabs.sendMessage(
      currentTab.id,
      { action: "GET_VIDEO_DATA" },
      (response) => {
        setBasicUiState({
          title: response?.title,
          channel: response?.channel,
          subtitle: response?.subscribers,
          thumbnailUrl: response?.thumbnailUrl,
        });
      },
    );
  });
});