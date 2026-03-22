import os
import subprocess

from flask import Flask, Response, jsonify, request
from flask_cors import CORS

app = Flask(__name__)
CORS(app)


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"ok": True}), 200


@app.route("/download", methods=["GET"])
def download():
    url = request.args.get("url")
    quality = request.args.get("quality", "best")
    if not url:
        return "Missing url parameter", 400
    if not url.startswith(("http://", "https://")):
        return "Invalid url parameter", 400

    # Map quality to yt-dlp format string
    quality_map = {
        "320p": "bestvideo[height<=320]+bestaudio/best[height<=320]",
        "360p": "bestvideo[height<=360]+bestaudio/best[height<=360]",
        "480p": "bestvideo[height<=480]+bestaudio/best[height<=480]",
        "720p": "bestvideo[height<=720]+bestaudio/best[height<=720]",
        "best": "bestvideo+bestaudio/best",
    }
    fmt = quality_map.get(quality, "bestvideo+bestaudio/best")

    ytdlp_cmd = [
        "yt-dlp",
        "--js-runtimes",
        "node",
        "--extractor-args",
        "youtube:player_client=web,android",
        "--sleep-requests",
        "2",
        "--retries",
        "5",
        "-f",
        fmt,
        "-o",
        "-",  # output to stdout
        url,
    ]

    cookies_file = os.environ.get("YTDLP_COOKIES_FILE", "cookies.txt")
    cookies_from_browser = os.environ.get("YTDLP_COOKIES_FROM_BROWSER", "")
    if os.path.exists(cookies_file):
        ytdlp_cmd[1:1] = ["--cookies", cookies_file]
    elif cookies_from_browser:
        ytdlp_cmd[1:1] = ["--cookies-from-browser", cookies_from_browser]

    try:
        proc = subprocess.Popen(ytdlp_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except FileNotFoundError:
        return jsonify({"error": "yt-dlp is not installed on server PATH"}), 500
    except Exception as exc:
        return jsonify({"error": f"Failed to start yt-dlp: {str(exc)}"}), 500

    first_chunk = proc.stdout.read(4096)
    if not first_chunk:
        proc.wait()
        err = proc.stderr.read().decode("utf-8", errors="ignore")
        app.logger.error("yt-dlp failed early: %s", err)
        return jsonify({"error": "yt-dlp failed", "details": err[:700]}), 502

    def generate():
        yield first_chunk
        for chunk in iter(lambda: proc.stdout.read(4096), b""):
            yield chunk
        proc.stdout.close()
        proc.wait()
        err = proc.stderr.read().decode("utf-8", errors="ignore")
        if proc.returncode != 0:
            app.logger.error("yt-dlp failed while streaming: %s", err)

    headers = {
        "Content-Disposition": 'attachment; filename="video.mp4"',
        "Content-Type": "video/mp4",
    }
    return Response(generate(), headers=headers)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
