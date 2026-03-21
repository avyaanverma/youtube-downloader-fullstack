# YouTube Downloader Python BackendThis backend uses Python, Flask, and yt-dlp to download YouTube videos in various qualities.## Setup1. 

**Install Python dependencies:**   

```bash   pip install flask flask-cors yt-dlp   ```2. **Run the backend server:**   ```bash   python yt_backend.py   ```   The server will start at `http://localhost:5000`.## Usage- To download a video, make a GET request to:  ```  http://localhost:5000/download?url=YOUTUBE_VIDEO_URL&quality=320p|480p|720p|best  ```- The video will be streamed as a download.## Example```GET http://localhost:5000/download?url=https://www.youtube.com/watch?v=dQw4w9WgXcQ&quality=720p```## Supported Qualities- 320p
- 360p
- 480p
- 720p
- best (default)

## Notes
- Make sure `yt-dlp` is installed and available in your PATH.
- This backend replaces any previous Node.js backend.
