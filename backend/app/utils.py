import subprocess
import json
import tempfile
import os


def base_command():
    return [
        "yt-dlp",
        "--no-warnings",
        "--extractor-args", "youtube:player_client=web"
    ]


def select_format(url: str, cookies: str = None):
    temp_cookie_file = None

    try:
        cmd = base_command()

        if cookies:
            temp = tempfile.NamedTemporaryFile(delete=False, mode='w')
            temp.write(cookies)
            temp.close()
            temp_cookie_file = temp.name
            cmd += ["--cookies", temp_cookie_file]

        cmd += [url, "--dump-json"]

        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            return result.stderr

        data = json.loads(result.stdout)

        formats = []
        for f in data.get("formats", []):
            if f.get("vcodec") != "none":
                formats.append({
                    "format_id": f.get("format_id"),
                    "resolution": f.get("resolution"),
                    "ext": f.get("ext")
                })

        return formats

    finally:
        if temp_cookie_file and os.path.exists(temp_cookie_file):
            os.remove(temp_cookie_file)


def download_video(url: str, format_id: str, cookies: str = None):
    temp_cookie_file = None

    try:
        cmd = base_command()

        if cookies:
            temp = tempfile.NamedTemporaryFile(delete=False, mode='w')
            temp.write(cookies)
            temp.close()
            temp_cookie_file = temp.name
            cmd += ["--cookies", temp_cookie_file]

        cmd += [url, "-f", format_id]

        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            return {"error": result.stderr}

        return {"status": "success"}

    finally:
        if temp_cookie_file and os.path.exists(temp_cookie_file):
            os.remove(temp_cookie_file)