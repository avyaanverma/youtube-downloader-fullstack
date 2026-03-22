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
