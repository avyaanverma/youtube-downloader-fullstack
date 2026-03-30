import os
import select
import subprocess
import sys
import time
import threading

from flask import Flask, Response, jsonify, request
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

IS_WINDOWS = sys.platform == "win32"


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


def drain_stderr(proc, stderr_lines):
    """
    Continuously read stderr in a background thread so the pipe
    never fills up and blocks yt-dlp (which would stall stdout too).
    """
    try:
        for line in iter(proc.stderr.readline, b""):
            stderr_lines.append(line)
    except Exception:
        pass
    finally:
        try:
            proc.stderr.close()
        except Exception:
            pass


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
        "-o", "-",
        url,
    ]

    try:
        proc = subprocess.Popen(
            ytdlp_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    except FileNotFoundError:
        return jsonify({"error": "yt-dlp is not installed on server PATH"}), 500
    except Exception as exc:
        return jsonify({"error": f"Failed to start yt-dlp: {str(exc)}"}), 500

    # KEY FIX: drain stderr continuously in a background thread.
    # Without this, the stderr OS pipe buffer (~64KB) fills up, yt-dlp
    # blocks trying to write logs, and stdout stalls — causing the
    # "12KB then frozen" symptom.
    stderr_lines = []
    stderr_thread = threading.Thread(
        target=drain_stderr, args=(proc, stderr_lines), daemon=True
    )
    stderr_thread.start()

    startup_timeout_s = int(os.environ.get("YTDLP_STARTUP_TIMEOUT", "90"))
    deadline = time.monotonic() + startup_timeout_s
    first_chunk = b""

    if IS_WINDOWS:
        result = []

        def read_first_chunk():
            try:
                data = proc.stdout.read(4096)
                if data:
                    result.append(data)
            except Exception:
                pass

        t = threading.Thread(target=read_first_chunk, daemon=True)
        t.start()

        while time.monotonic() < deadline:
            t.join(timeout=1.0)
            if result or not t.is_alive():
                break
            if proc.poll() is not None:
                break

        if result:
            first_chunk = result[0]

    else:
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
            stderr_thread.join(timeout=3)
            err = b"".join(stderr_lines).decode("utf-8", errors="ignore")
            msg = f"yt-dlp startup timeout after {startup_timeout_s}s"
            app.logger.error("%s\n%s", msg, err)
            return jsonify(
                {
                    "error": "yt-dlp startup timeout",
                    "message": "Video initialization took too long. Please retry.",
                    "details": msg,
                }
            ), 504

        stderr_thread.join(timeout=3)
        err = b"".join(stderr_lines).decode("utf-8", errors="ignore")
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
        try:
            for chunk in iter(lambda: proc.stdout.read(65536), b""):
                yield chunk
        finally:
            proc.stdout.close()
            proc.wait()
            stderr_thread.join(timeout=5)
            if proc.returncode != 0:
                err = b"".join(stderr_lines).decode("utf-8", errors="ignore")
                app.logger.error("yt-dlp failed while streaming (rc=%d): %s", proc.returncode, err)

    headers = {
        "Content-Disposition": 'attachment; filename="video.mp4"',
        "Content-Type": "video/mp4",
        # Tell the browser/proxy not to buffer — stream straight through
        "X-Accel-Buffering": "no",
        "Cache-Control": "no-cache",
    }
    return Response(generate(), headers=headers, direct_passthrough=True)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    # Use threaded=True so each download gets its own thread and
    # the generator isn't starved by other requests
    app.run(host="0.0.0.0", port=port, threaded=True)