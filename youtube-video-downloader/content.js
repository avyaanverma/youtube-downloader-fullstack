function extractVideoIdFromUrl(url) {
  try {
    const parsed = new URL(url);

    if (parsed.hostname === "youtu.be") {
      return parsed.pathname.replace("/", "") || null;
    }

    if (parsed.pathname.startsWith("/shorts/")) {
      return parsed.pathname.split("/shorts/")[1]?.split("/")[0] || null;
    }

    return parsed.searchParams.get("v");
  } catch (error) {
    return null;
  }
}

function getVideoData() {
  const title =
    document.querySelector("ytd-watch-metadata h1 yt-formatted-string")?.innerText ||
    document.querySelector('meta[property="og:title"]')?.content ||
    document.title.replace(" - YouTube", "");

  const channel =
    document.querySelector("ytd-channel-name a")?.innerText ||
    document.querySelector('meta[itemprop="author"]')?.content ||
    "";

  const subscribers = document.querySelector("#owner-sub-count")?.innerText || "";

  const videoId = extractVideoIdFromUrl(window.location.href);
  const thumbnailUrl =
    document.querySelector('meta[property="og:image"]')?.content ||
    (videoId ? `https://img.youtube.com/vi/${videoId}/hqdefault.jpg` : "");

  return {
    title,
    channel,
    subscribers,
    thumbnailUrl,
    videoId,
  };
}

chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === "GET_VIDEO_DATA") {
    sendResponse(getVideoData());
  }
});
