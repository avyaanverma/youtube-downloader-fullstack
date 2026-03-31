import os
import sys
import subprocess
import json


COOKIE_FILE_PATH = os.path.join(os.path.dirname(__file__), "cookies.txt")


def _cookie_file_exists():
    return os.path.isfile(COOKIE_FILE_PATH) and os.path.getsize(COOKIE_FILE_PATH) > 0


def _base_ytdlp_args():
    # Use cookies-capable client when cookies.txt exists unless overridden by env.
    # You can override via env: YTDLP_PLAYER_CLIENT=web/ios/tv/etc.
    env_client = os.environ.get("YTDLP_PLAYER_CLIENT")
    if env_client:
        player_client = env_client
    else:
        player_client = "web" if _cookie_file_exists() else "android"
    return ["yt-dlp", "--extractor-args", f"youtube:player_client={player_client}"]


def _backend_cookie_file():
    if _cookie_file_exists():
        return COOKIE_FILE_PATH
    return None


def has_ytdlp() -> bool:
    try:
        subprocess.run(["yt-dlp", "-h"], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except:
        return False


def select_format(url: str):
    format_ids = []
    cookie_file = _backend_cookie_file()

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
    cookie_file = _backend_cookie_file()

    command = _base_ytdlp_args()
    if cookie_file:
        command += ["--cookies", cookie_file]
    command += [url, "-f", format_id]

    try:
        subprocess.run(command, check=True)
        return {"status": "success"}
    except subprocess.CalledProcessError as e:
        return {"error": str(e)}

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
