import os
import subprocess
import tempfile

from flask import Flask, Response, jsonify, request
from flask_cors import CORS

app = Flask(__name__)
CORS(app)


def resolve_cookie_args():
    """
    Resolve yt-dlp auth flags in a deployment-friendly order:
    1) YTDLP_COOKIES_CONTENT (raw Netscape cookies content)
    2) YTDLP_COOKIES_FILE (path mounted on server)
    3) YTDLP_COOKIES_FROM_BROWSER (local/dev only)
    """
    cookies_content = os.environ.get("YTDLP_COOKIES_CONTENT", "").strip()
    cookies_file = os.environ.get("YTDLP_COOKIES_FILE", "cookies.txt")
    cookies_from_browser = os.environ.get("YTDLP_COOKIES_FROM_BROWSER", "").strip()

    # Some platforms store multiline env content as literal \n; normalize it.
    if "\\n" in cookies_content and "\n" not in cookies_content:
        cookies_content = cookies_content.replace("\\n", "\n")

    if cookies_content:
        temp_path = os.path.join(tempfile.gettempdir(), "yt_cookies.txt")
        with open(temp_path, "w", encoding="utf-8") as fh:
            fh.write(cookies_content)
        return ["--cookies", temp_path]

    if os.path.exists(cookies_file):
        return ["--cookies", cookies_file]

    if cookies_from_browser:
        return ["--cookies-from-browser", cookies_from_browser]

    return []


def classify_ytdlp_error(stderr_text):
    lowered = (stderr_text or "").lower()
    if "sign in to confirm you" in lowered and "not a bot" in lowered:
        return {
            "error": "youtube_bot_check",
            "message": (
                "YouTube blocked anonymous access for this video. "
                "Set YTDLP_COOKIES_CONTENT (recommended in cloud deploy), "
                "or YTDLP_COOKIES_FILE, then redeploy."
            ),
        }
    return {"error": "yt-dlp failed", "message": "yt-dlp failed"}


@app.route("/health", methods=["GET"])
def health():
    raw = os.environ.get("YTDLP_COOKIES_CONTENT", "")
    return jsonify(
        {
            "ok": True,
            "cookies_env_present": bool(raw),
            "cookies_env_len": len(raw),
            "has_real_newline": "\n" in raw,
            "has_escaped_newline": "\\n" in raw,
        }
    ), 200


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

    cookie_args = resolve_cookie_args()

    # Android client does not support cookies in yt-dlp.
    player_client = "web" if cookie_args else "web,android"

    ytdlp_cmd = [
        "yt-dlp",
        "--js-runtimes",
        "node",
        "--extractor-args",
        f"youtube:player_client={player_client}",
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

    if cookie_args:
        ytdlp_cmd[1:1] = cookie_args

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