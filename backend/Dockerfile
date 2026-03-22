FROM python:3.10-slim

WORKDIR /app

COPY . .

# ffmpeg for muxing + nodejs for yt-dlp JS challenge runtime
RUN apt-get update && apt-get install -y ffmpeg nodejs npm && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir -r requirements.txt

CMD ["gunicorn", "-w", "2", "--timeout", "180", "--graceful-timeout", "30", "-b", "0.0.0.0:10000", "yt_backend:app"]
