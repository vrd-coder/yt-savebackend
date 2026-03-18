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
            # Bypass bot detection
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-us,en;q=0.5',
                'Sec-Fetch-Mode': 'navigate',
            },
            'extractor_args': {
                'youtube': {
                    'player_client': ['android', 'web'],
                    'player_skip': ['webpage', 'config', 'js'],
                }
            },
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)

        # Get video formats (with both video+audio)
        formats = []
        seen = set()
        for f in info.get('formats', []):
            if f.get('vcodec') != 'none' and f.get('acodec') != 'none':
                quality = f.get('format_note') or f.get('quality') or 'unknown'
                if quality not in seen and f.get('url'):
                    seen.add(quality)
                    formats.append({
                        'quality': quality,
                        'url': f.get('url'),
                        'ext': f.get('ext', 'mp4'),
                        'filesize': f.get('filesize'),
                    })

        # Get best audio
        audio_url = None
        for f in info.get('formats', []):
            if f.get('acodec') != 'none' and f.get('vcodec') == 'none' and f.get('url'):
                audio_url = f.get('url')
                break

        return jsonify({
            'title': info.get('title', 'YouTube Video'),
            'thumbnail': info.get('thumbnail', ''),
            'duration': info.get('duration', 0),
            'author': info.get('uploader', ''),
            'formats': formats[-6:],
            'audio_url': audio_url,
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
    
