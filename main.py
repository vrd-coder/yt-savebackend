from flask import Flask, request, jsonify
from flask_cors import CORS
import yt_dlp
import os

app = Flask(__name__)
CORS(app)

@app.route('/')
def home():
    return jsonify({"status": "YTSave API running ✅"})

@app.route('/info')
def get_info():
    url = request.args.get('url')
    if not url:
        return jsonify({"error": "url required"}), 400

    try:
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)

        # Get video formats
        formats = []
        seen = set()
        for f in info.get('formats', []):
            if f.get('vcodec') != 'none' and f.get('acodec') != 'none':
                quality = f.get('format_note') or f.get('quality') or 'unknown'
                if quality not in seen:
                    seen.add(quality)
                    formats.append({
                        'quality': quality,
                        'url': f.get('url'),
                        'ext': f.get('ext', 'mp4'),
                        'filesize': f.get('filesize'),
                    })

        # Get audio format
        audio_url = None
        for f in info.get('formats', []):
            if f.get('acodec') != 'none' and f.get('vcodec') == 'none':
                if f.get('ext') == 'm4a' or f.get('ext') == 'webm':
                    audio_url = f.get('url')
                    break

        return jsonify({
            'title': info.get('title', 'YouTube Video'),
            'thumbnail': info.get('thumbnail', ''),
            'duration': info.get('duration', 0),
            'author': info.get('uploader', ''),
            'formats': formats[-6:],  # last 6 = best quality ones
            'audio_url': audio_url,
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
  
