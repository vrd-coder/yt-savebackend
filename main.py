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
    return jsonify({"status": "YTSave API running 🚀"})

# 🎯 VIDEO INFO
@app.route('/info')
def info():
    url = request.args.get('url')

    try:
        ydl_opts = {
            'quiet': True,
            'skip_download': True,
            'extract_flat': True  # 🔥 FAST FIX
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            data = ydl.extract_info(url, download=False)

        return jsonify({
            "title": data.get("title"),
            "thumbnail": data.get("thumbnail"),
            "author": data.get("uploader")
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500
# 📥 DOWNLOAD (SIMPLE + STABLE)
@app.route('/download')
def download():
    url = request.args.get('url')

    file_id = str(uuid.uuid4())
    filepath = os.path.join(DOWNLOAD_DIR, f"{file_id}.mp4")

    ydl_opts = {
        'outtmpl': filepath,
        'format': 'best',   # 🔥 SIMPLE (no ffmpeg issue)
        'quiet': True
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
