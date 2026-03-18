from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import yt_dlp
import os
import uuid

app = Flask(__name__)
CORS(app)

DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

@app.route('/')
def home():
    return jsonify({"status": "YTSave API running 🚀"})


# ✅ VIDEO INFO
@app.route('/info')
def info():
    url = request.args.get('url')
    if not url:
        return jsonify({"error": "url required"}), 400

    try:
        with yt_dlp.YoutubeDL({'quiet': True}) as ydl:
            data = ydl.extract_info(url, download=False)

        return jsonify({
            "title": data.get("title"),
            "thumbnail": data.get("thumbnail"),
            "duration": data.get("duration"),
            "author": data.get("uploader")
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ✅ DOWNLOAD (NO FFMPEG NEEDED)
@app.route('/download')
def download():
    url = request.args.get('url')
    if not url:
        return jsonify({"error": "url required"}), 400

    try:
        file_id = str(uuid.uuid4())
        filepath = os.path.join(DOWNLOAD_DIR, f"{file_id}.mp4")

        ydl_opts = {
            'outtmpl': filepath,
            'format': 'bestvideo+bestaudio/best',
            'merge_output_format': 'mp4',
            'quiet': True,
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

        return jsonify({
            "download_url": f"/file/{file_id}"
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ✅ SERVE FILE
@app.route('/file/<file_id>')
def serve_file(file_id):
    path = os.path.join(DOWNLOAD_DIR, f"{file_id}.mp4")

    if not os.path.exists(path):
        return jsonify({"error": "File not found"}), 404

    return send_file(path, as_attachment=True)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
