import os
import select
import subprocess
import time

from flask import Flask, Response, jsonify, request
from flask_cors import CORS

app = Flask(__name__)
CORS(app)


def classify_ytdlp_error(stderr_text):
    lowered = (stderr_text or "").lower()
    if "sign in to confirm you" in lowered and "not a bot" in lowered:
        return {
            "error": "youtube_bot_check",
            "message": (
                "YouTube blocked anonymous access for this video. "
                "bgutil po_token may have failed. Check bgutil service."
            ),
        }
    return {"error": "yt-dlp failed", "message": "yt-dlp failed"}


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

    bgutil_url = os.environ.get("BGUTIL_URL", "http://localhost:4416").rstrip("/")

    ytdlp_cmd = [
        "yt-dlp",
        "--js-runtimes", "node",
        "--extractor-args",
        f"youtube:player_client=web,android;youtubepot-bgutilhttp:base_url={bgutil_url}",
        "--sleep-requests", "2",
        "--retries", "5",
        "-f", fmt,
        "-o", "-",  # output to stdout
        url,
    ]

    try:
        proc = subprocess.Popen(ytdlp_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except FileNotFoundError:
        return jsonify({"error": "yt-dlp is not installed on server PATH"}), 500
    except Exception as exc:
        return jsonify({"error": f"Failed to start yt-dlp: {str(exc)}"}), 500

    startup_timeout_s = int(os.environ.get("YTDLP_STARTUP_TIMEOUT", "90"))
    deadline = time.monotonic() + startup_timeout_s
    first_chunk = b""

    while time.monotonic() < deadline:
        if proc.poll() is not None:
            break

        ready, _, _ = select.select([proc.stdout], [], [], 1.0)
        if ready:
            first_chunk = proc.stdout.read(4096)
            if first_chunk:
                break

    if not first_chunk:
        if proc.poll() is None:
            proc.terminate()
            err = f"yt-dlp startup timeout after {startup_timeout_s}s"
            app.logger.error(err)
            return jsonify(
                {
                    "error": "yt-dlp startup timeout",
                    "message": "Video initialization took too long. Please retry.",
                    "details": err,
                }
            ), 504

        err = proc.stderr.read().decode("utf-8", errors="ignore")
        app.logger.error("yt-dlp failed early: %s", err)
        classified = classify_ytdlp_error(err)
        return jsonify(
            {
                "error": classified["error"],
                "message": classified["message"],
                "details": err[:700],
            }
        ), 502

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