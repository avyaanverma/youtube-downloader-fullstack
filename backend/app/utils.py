import os
import sys
import subprocess 
import json

def has_ytdlp() -> bool:
    try:
        subprocess.run(["yt-dlp", "-h"], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except:
        return False

def select_format(url : str) -> str:
    format_ids = []
    # Fetch video info json
    try:
        output = subprocess.run(["yt-dlp", url, "--dump-json"], text=True, capture_output=True, check=True)
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
                "url": f.get("url")  # 🔥 THIS is what frontend needs
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
    command = ["yt-dlp", url, "-f", format_id]

    try:
        subprocess.run(command, check=True)
        return {"status": "success"}
    except subprocess.CalledProcessError as e:
        return {"error": str(e)}
# def main():
#     if(has_ytdlp() is  False):
#        print("yt-dlp isn't installed")
#        sys.exit()

#     url = input("Enter video URL (q to quit): ")

#     if url.lower() == "q":
#         sys.exit()

#     # List formats
#     format_id = select_format(url)
    
#     # Confirm Download
#     if format_id != "" : 
#         confirm = confirm_download()
#         if not confirm:
#             print("Download cancelled.")
#         else: 
#             download_video(url, format_id)
    