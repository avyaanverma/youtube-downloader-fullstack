# YouTube Downloader Python Backend

This backend uses Python, Flask, and `yt-dlp` to download YouTube videos in different qualities.

## Local Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Run the server:
```bash
python yt_backend.py
```

Server starts on `http://localhost:5000`.

## API Usage

- Health check:
```http
GET /health
```

- Download endpoint:
```http
GET /download?url=YOUTUBE_VIDEO_URL&quality=320p|360p|480p|720p|best
```

Example:
```http
GET http://localhost:5000/download?url=https://www.youtube.com/watch?v=dQw4w9WgXcQ&quality=720p
```

## Deploy (Render / Railway)

This folder is deployment-ready with:
- `requirements.txt`
- `Procfile`
- `runtime.txt`

Start command:
```bash
gunicorn yt_backend:app
```

The app auto-uses platform `PORT` env var in production.

## Fix "Sign in to confirm you're not a bot" in Deploy

On cloud servers, `--cookies-from-browser` usually does not work (no browser profile exists).
Use one of these env vars:

1. `YTDLP_COOKIES_CONTENT` (recommended)
- Put full Netscape-format cookies text in this env var.
- Backend writes it to a temp file and passes `--cookies` to yt-dlp.

2. `YTDLP_COOKIES_FILE`
- Path to a cookies file already present in container/storage.

3. `YTDLP_COOKIES_FROM_BROWSER`
- Best for local/dev only.

Priority order used by backend:
`YTDLP_COOKIES_CONTENT` -> `YTDLP_COOKIES_FILE` -> `YTDLP_COOKIES_FROM_BROWSER`.

If YouTube bot-check blocks a video, API now returns:
- `error: "youtube_bot_check"`
- a human-readable `message`
- raw yt-dlp `details` snippet for debugging.