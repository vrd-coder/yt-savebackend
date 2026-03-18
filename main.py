from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import yt_dlp
import os
import uuid
import threading
import time
import random

app = Flask(__name__)
CORS(app)

DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# 🔥 MULTIPLE COOKIES
COOKIE_FILES = [
    "cookies.txt",
    "cookies2.txt",
]

# 🧹 AUTO DELETE
def delete_file_later(path):
    def task():
        time.sleep(600)
        if os.path.exists(path):
            os.remove(path)
    threading.Thread(target=task).start()


@app.route('/')
def home():
    return jsonify({"status": "YTSave API running 🚀"})


# 🎯 INFO
@app.route('/info')
def info():
    url = request.args.get('url')

    try:
        if "shorts" in url:
            url = url.replace("shorts/", "watch?v=")

        cookie_file = random.choice(COOKIE_FILES)

        ydl_opts = {
        'outtmpl': filepath,
        'format': 'bestvideo*+bestaudio/best',
        'merge_output_format': 'mp4',
        'quiet': True,
        'cookiefile': cookie_file
}
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


# 📥 DOWNLOAD
@app.route('/download')
def download():
    url = request.args.get('url')

    try:
        if "shorts" in url:
            url = url.replace("shorts/", "watch?v=")

        file_id = str(uuid.uuid4())
        filepath = os.path.join(DOWNLOAD_DIR, f"{file_id}.mp4")

        cookie_file = random.choice(COOKIE_FILES)

        ydl_opts = {
            'outtmpl': filepath,
            'format': 'bv*+ba/best',
            'merge_output_format': 'mp4',
            'quiet': True,
            'cookiefile': cookie_file
        }

        # 🔥 TRY WITH COOKIE
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])

        # 🔥 FALLBACK WITHOUT COOKIE
        except:
            ydl_opts.pop('cookiefile', None)

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])

        delete_file_later(filepath)

        return jsonify({
            "download_url": f"/file/{file_id}"
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


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
