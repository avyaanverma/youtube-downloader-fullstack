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
        output = subprocess.run(["yt-dlp", url, "--dump-json"], capture_output=True, check=True)
        output = json.loads(output.stdout)
    except subprocess.CalledProcessError as e:
        print(f"{e.returncode} : {e.stderr}")
        return ""
    
    # List the formats
    if "formats" not in output:
        print("No formats available for that URL.")
        return ""

    for video in enumerate(output["formats"]):
        print(f"{video[0]} - {video[1]["resolution"]} - {video[1]["ext"]}");
        format_ids.append(video[1]["format_id"])

    # Prompt user
    while True:
        choice = input("Select a resolution by number [q to quit]: ")

        if choice == "q":
            return ""
        elif not choice.isdigit():
            print("Option must be a non-negative number. Please try again")
        choice = int(choice)
        if choice >= len(format_ids):
            print("Invalid choice. Please try again")
        else:
            return format_ids[choice]

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
        print("Download complete")
    except subprocess.CalledProcessError as e:
        print(f"Error during download.\n{f.returncode} : {e.stderr}")
        os.system("pause")
def main():
    if(has_ytdlp() is  False):
       print("yt-dlp isn't installed")
       sys.exit()

    url = input("Enter video URL (q to quit): ")

    if url.lower() == "q":
        sys.exit()

    # List formats
    format_id = select_format(url)
    
    # Confirm Download
    if format_id != "" : 
        confirm = confirm_download()
        if not confirm:
            print("Download cancelled.")
        else: 
            download_video(url, format_id)
    


if __name__=="__main__":
    main()