from flask import Flask, request, jsonify, Response
from flask_cors import CORS
import yt_dlp
import os
import subprocess
import tempfile

app = Flask(__name__)
CORS(app)

COOKIES_FILE = os.path.join(os.path.dirname(__file__), 'www.youtube.com_cookies.txt')

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
        }

        if os.path.exists(COOKIES_FILE):
            ydl_opts['cookiefile'] = COOKIES_FILE

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)

        all_formats = info.get('formats', [])

        # Combined video+audio formats
        combined = {}
        for f in all_formats:
            if (f.get('vcodec', 'none') != 'none' and
                f.get('acodec', 'none') != 'none' and
                f.get('url')):
                h = f.get('height') or 0
                q = f.get('format_note') or (str(h)+'p' if h else 'SD')
                if h not in combined:
                    combined[h] = {
                        'quality': q,
                        'url': f.get('url'),
                        'ext': 'mp4',
                        'height': h,
                        'needs_merge': False,
                    }

        # Best audio
        audio_url = None
        best_abr = 0
        for f in all_formats:
            if (f.get('acodec', 'none') != 'none' and
                f.get('vcodec', 'none') == 'none' and
                f.get('url')):
                abr = f.get('abr') or 0
                if abr > best_abr:
                    best_abr = abr
                    audio_url = f.get('url')

        # Video-only for 720p/1080p merge
        if audio_url:
            for f in all_formats:
                if (f.get('vcodec', 'none') != 'none' and
                    f.get('acodec', 'none') == 'none' and
                    f.get('url')):
                    h = f.get('height') or 0
                    if h >= 720 and h not in combined:
                        q = f.get('format_note') or (str(h)+'p' if h else 'HD')
                        combined[h] = {
                            'quality': q,
                            'video_url': f.get('url'),
                            'audio_url': audio_url,
                            'ext': 'mp4',
                            'height': h,
                            'needs_merge': True,
                        }

        formats = sorted(combined.values(), key=lambda x: x.get('height', 0))

        # Fallback - use best available format directly
        if not formats:
            best_url = info.get('url', '')
            if best_url:
                formats = [{'quality': 'Best', 'url': best_url, 'ext': 'mp4', 'needs_merge': False}]

        return jsonify({
            'title': info.get('title', 'YouTube Video'),
            'thumbnail': info.get('thumbnail', ''),
            'duration': info.get('duration', 0),
            'author': info.get('uploader', ''),
            'formats': formats,
            'audio_url': audio_url,
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/merge')
def merge_video():
    video_url = request.args.get('video_url')
    audio_url = request.args.get('audio_url')
    title     = request.args.get('title', 'video')

    if not video_url or not audio_url:
        return jsonify({"error": "video_url and audio_url required"}), 400

    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            out_path = os.path.join(tmpdir, 'output.mp4')
            cmd = [
                'ffmpeg', '-y',
                '-i', video_url,
                '-i', audio_url,
                '-c:v', 'copy',
                '-c:a', 'aac',
                '-movflags', 'faststart',
                out_path
            ]
            result = subprocess.run(cmd, capture_output=True, timeout=120)
            if result.returncode != 0:
                return jsonify({"error": "Merge failed"}), 500

            filename = title.replace(' ', '_')[:50] + '.mp4'
            with open(out_path, 'rb') as f:
                data = f.read()

            return Response(
                data,
                mimetype='video/mp4',
                headers={
                    'Content-Disposition': f'attachment; filename="{filename}"',
                    'Content-Length': str(len(data))
                }
            )
    except subprocess.TimeoutExpired:
        return jsonify({"error": "Timeout"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
    
