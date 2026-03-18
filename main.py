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
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            },
            'extractor_args': {
                'youtube': {
                    'player_client': ['android'],
                }
            },
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)

        all_formats = info.get('formats', [])

        # Get combined video+audio formats
        combined = []
        for f in all_formats:
            if (f.get('vcodec', 'none') != 'none' and
                f.get('acodec', 'none') != 'none' and
                f.get('url')):
                combined.append({
                    'quality': f.get('format_note') or f.get('height') or 'SD',
                    'url': f.get('url'),
                    'ext': f.get('ext', 'mp4'),
                })

        # If no combined formats, get best video-only formats
        if not combined:
            seen_heights = set()
            for f in all_formats:
                h = f.get('height')
                if (f.get('vcodec', 'none') != 'none' and
                    f.get('url') and h and h not in seen_heights):
                    seen_heights.add(h)
                    combined.append({
                        'quality': f'{h}p',
                        'url': f.get('url'),
                        'ext': f.get('ext', 'mp4'),
                    })

        # Get best audio URL
        audio_url = None
        for f in all_formats:
            if (f.get('acodec', 'none') != 'none' and
                f.get('vcodec', 'none') == 'none' and
                f.get('url')):
                audio_url = f.get('url')
                break

        # Fallback — use direct URL if available
        if not combined and info.get('url'):
            combined.append({
                'quality': 'Best',
                'url': info.get('url'),
                'ext': 'mp4',
            })

        return jsonify({
            'title': info.get('title', 'YouTube Video'),
            'thumbnail': info.get('thumbnail', ''),
            'duration': info.get('duration', 0),
            'author': info.get('uploader', ''),
            'formats': combined[-6:],
            'audio_url': audio_url,
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
                
