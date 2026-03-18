from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import yt_dlp
import os
import uuid
import threading
import time

app = Flask(__name__)
CORS(app)

DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)


# 🧹 AUTO DELETE
def delete_file_later(path):
    def task():
        time.sleep(600)  # 10 min
        if os.path.exists(path):
            os.remove(path)
    threading.Thread(target=task).start()


@app.route('/')
def home():
    return jsonify({"status": "YTSave PRO API 🚀"})


# 🎯 VIDEO INFO + FORMATS
@app.route('/info')
def info():
    url = request.args.get('url')

    with yt_dlp.YoutubeDL({'quiet': True}) as ydl:
        info = ydl.extract_info(url, download=False)

    formats = []

    for f in info.get('formats', []):
        if f.get('vcodec') != 'none' and f.get('height'):
            formats.append({
                "quality": f"{f.get('height')}p",
                "height": f.get('height')
            })

    # unique + sorted
    formats = sorted({f['height']: f for f in formats}.values(), key=lambda x: x['height'])

    return jsonify({
        "title": info.get("title"),
        "thumbnail": info.get("thumbnail"),
        "author": info.get("uploader"),
        "formats": formats[-5:]  # best qualities
    })


# 📥 DOWNLOAD
@app.route('/download')
def download():
    url = request.args.get('url')
    quality = request.args.get('quality')

    file_id = str(uuid.uuid4())
    filepath = os.path.join(DOWNLOAD_DIR, f"{file_id}.mp4")

    if quality:
        format_str = f"bestvideo[height<={quality}]+bestaudio/best[height<={quality}]"
    else:
        format_str = "bestvideo+bestaudio/best"

    ydl_opts = {
        'outtmpl': filepath,
        'format': format_str,
        'merge_output_format': 'mp4',
        'quiet': True,
        'concurrent_fragment_downloads': 5
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])

    delete_file_later(filepath)

    return jsonify({
        "download_url": f"/file/{file_id}"
    })


# 📦 SERVE FILE
@app.route('/file/<file_id>')
def serve_file(file_id):
    path = os.path.join(DOWNLOAD_DIR, f"{file_id}.mp4")

    if not os.path.exists(path):
        return jsonify({"error": "File expired"}), 404

    return send_file(path, as_attachment=True)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
