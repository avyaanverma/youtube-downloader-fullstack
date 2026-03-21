from flask import Flask, request, Response
from flask_cors import CORS
import subprocess

app = Flask(__name__)
CORS(app)

@app.route('/download', methods=['GET'])
def download():
    url = request.args.get('url')
    quality = request.args.get('quality', 'best')
    if not url:
        return "Missing url parameter", 400

    # Map quality to yt-dlp format string
    quality_map = {
        '320p': 'bestvideo[height<=320]+bestaudio/best[height<=320]',
        '360p': 'bestvideo[height<=360]+bestaudio/best[height<=360]',
        '480p': 'bestvideo[height<=480]+bestaudio/best[height<=480]',
        '720p': 'bestvideo[height<=720]+bestaudio/best[height<=720]',
        'best': 'bestvideo+bestaudio/best'
    }
    fmt = quality_map.get(quality, 'bestvideo+bestaudio/best')

    def generate():
        ytdlp_cmd = [
            'yt-dlp',
            '-f', fmt,
            '-o', '-',  # output to stdout
            url
        ]
        proc = subprocess.Popen(ytdlp_cmd, stdout=subprocess.PIPE)
        for chunk in iter(lambda: proc.stdout.read(4096), b''):
            yield chunk
        proc.stdout.close()
        proc.wait()

    headers = {
        'Content-Disposition': 'attachment; filename="video.mp4"',
        'Content-Type': 'video/mp4'
    }
    return Response(generate(), headers=headers)

if __name__ == '__main__':
    app.run(port=5000)
