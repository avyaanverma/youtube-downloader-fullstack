import {CONFIG} from "./config.js"

const BACKEND_BASE_URL = CONFIG.BASE_URL;
const DOWNLOAD_QUALITIES = ["320p", "480p", "720p"];

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

function wireDownloadButtons(videoUrl) {
  const downloadBtns = document.querySelectorAll(".download-btn");

  downloadBtns.forEach((btn, idx) => {
    btn.onclick = () => {
      const quality = DOWNLOAD_QUALITIES[idx] || "best";
      const backendUrl = `${BACKEND_BASE_URL}/download?url=${encodeURIComponent(videoUrl)}&quality=${encodeURIComponent(quality)}`;
      window.open(backendUrl, "_blank");
    };
  });
}

document.addEventListener("DOMContentLoaded", () => {
  chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
    const currentTab = tabs && tabs[0];
    const videoUrl = currentTab?.url || "";

    if (!currentTab?.id || !isYouTubeVideoUrl(videoUrl)) {
      setBasicUiState({
        title: "No YouTube watch page",
        channel: "Go to a YouTube video and reopen popup",
        subtitle: "",
      });
      return;
    }

    wireDownloadButtons(videoUrl);

    chrome.tabs.sendMessage(
      currentTab.id,
      { action: "GET_VIDEO_DATA" },
      (response) => {
        if (chrome.runtime.lastError) {
          setBasicUiState({
            title: "Could not read video data",
            channel: "Reload the YouTube tab and try again",
            subtitle: chrome.runtime.lastError.message || "",
          });
          return;
        }

        setBasicUiState({
          title: response?.title || "YouTube Video",
          channel: response?.channel || "Unknown channel",
          subtitle: response?.subscribers || "",
          thumbnailUrl: response?.thumbnailUrl || "",
        });
      },
    );
  });
});
