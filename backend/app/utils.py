import os
import sys
import subprocess
import json
import tempfile


COOKIE_FILE_PATH = os.path.join(os.path.dirname(__file__), "cookies.txt")


def _cookie_file_exists(path: str) -> bool:
    return bool(path) and os.path.isfile(path) and os.path.getsize(path) > 0


def _cookies_available() -> bool:
    if os.environ.get("YTDLP_COOKIES"):
        return True
    env_path = os.environ.get("YTDLP_COOKIES_FILE") or os.environ.get("COOKIES_FILE")
    if _cookie_file_exists(env_path):
        return True
    return _cookie_file_exists(COOKIE_FILE_PATH)


def _base_ytdlp_args():
    # Use cookies-capable client when cookies exist unless overridden by env.
    # You can override via env: YTDLP_PLAYER_CLIENT=web/ios/tv/etc.
    env_client = os.environ.get("YTDLP_PLAYER_CLIENT")
    if env_client:
        player_client = env_client
    else:
        player_client = "web" if _cookies_available() else "android"
    return ["yt-dlp", "--extractor-args", f"youtube:player_client={player_client}"]


def _cookie_file_from_env():
    env_path = os.environ.get("YTDLP_COOKIES_FILE") or os.environ.get("COOKIES_FILE")
    if _cookie_file_exists(env_path):
        return env_path, False

    env_content = os.environ.get("YTDLP_COOKIES")
    if env_content:
        temp_file = tempfile.NamedTemporaryFile(delete=False, mode="w", encoding="utf-8", newline="\n")
        temp_file.write(env_content.strip() + "\n")
        temp_file.close()
        return temp_file.name, True

    return None, False


def _backend_cookie_file():
    env_path, cleanup = _cookie_file_from_env()
    if env_path:
        return env_path, cleanup
    if _cookie_file_exists(COOKIE_FILE_PATH):
        return COOKIE_FILE_PATH, False
    return None, False


def has_ytdlp() -> bool:
    try:
        subprocess.run(["yt-dlp", "-h"], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except:
        return False


def select_format(url: str):
    format_ids = []
    cookie_file, cleanup_cookie = _backend_cookie_file()

    # Fetch video info json
    try:
        cmd = _base_ytdlp_args()
        if cookie_file:
            cmd += ["--cookies", cookie_file]
        cmd += [url, "--dump-json"]

        output = subprocess.run(cmd, text=True, capture_output=True, check=True)
        output = json.loads(output.stdout)
    except subprocess.CalledProcessError as e:
        return f"{e.returncode} : {e.stderr}"
    finally:
        if cleanup_cookie and cookie_file:
            try:
                os.remove(cookie_file)
            except OSError:
                pass

    # List the formats
    if "formats" not in output:
        return {"No formats available for that URL."}

    for f in output.get("formats", []):
        if f.get("vcodec") != "none":  # filter only video
            format_ids.append({
                "format_id": f.get("format_id"),
                "resolution": f.get("resolution"),
                "ext": f.get("ext"),
                "url": f.get("url")  # THIS is what frontend needs
            })

    return format_ids


def confirm_download() -> bool:
    while True:
        confirm = input("Download? [Y/N]")

        if confirm.lower() == "n":
            return False
        elif confirm.lower() in ["y", ""]:
            return True


def download_video(url: str, format_id: str):
    cookie_file, cleanup_cookie = _backend_cookie_file()

    command = _base_ytdlp_args()
    if cookie_file:
        command += ["--cookies", cookie_file]
    command += [url, "-f", format_id]

    try:
        subprocess.run(command, check=True)
        return {"status": "success"}
    except subprocess.CalledProcessError as e:
        return {"error": str(e)}
    finally:
        if cleanup_cookie and cookie_file:
            try:
                os.remove(cookie_file)
            except OSError:
                pass

# def main():
#     if(has_ytdlp() is  False):
#        print("yt-dlp isn't installed")
#        sys.exit()
#
#     url = input("Enter video URL (q to quit): ")
#
#     if url.lower() == "q":
#         sys.exit()
#
#     # List formats
#     format_id = select_format(url)
#
#     # Confirm Download
#     if format_id != "" :
#         confirm = confirm_download()
#         if not confirm:
#             print("Download cancelled.")
#         else:
#             download_video(url, format_id)
