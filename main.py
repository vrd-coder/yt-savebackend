from flask import Flask, request, jsonify, Response
from flask_cors import CORS
import yt_dlp
import os
import subprocess
import tempfile
import threading

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
                    'player_client': ['web', 'android'],
                }
            },
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)

        all_formats = info.get('formats', [])

        # Combined formats (have both video+audio)
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
                        'ext': f.get('ext', 'mp4'),
                        'height': h,
                        'needs_merge': False,
                    }

        # Video-only formats for 1080p+ (needs merge)
        video_only = {}
        for f in all_formats:
            if (f.get('vcodec', 'none') != 'none' and
                f.get('acodec', 'none') == 'none' and
                f.get('url') and
                f.get('ext') == 'mp4'):
                h = f.get('height') or 0
                if h >= 1080 and h not in combined:
                    q = f.get('format_note') or (str(h)+'p' if h else 'HD')
                    video_only[h] = {
                        'quality': q,
                        'video_url': f.get('url'),
                        'ext': 'mp4',
                        'height': h,
                        'needs_merge': True,
                        'format_id': f.get('format_id'),
                    }

        # Best audio url
        audio_url = None
        audio_format_url = None
        best_abr = 0
        for f in all_formats:
            if (f.get('acodec', 'none') != 'none' and
                f.get('vcodec', 'none') == 'none' and
                f.get('url')):
                abr = f.get('abr') or 0
                if abr > best_abr:
                    best_abr = abr
                    audio_url = f.get('url')
                    audio_format_url = f.get('url')

        # Add video_only with audio url for merge
        for h, fmt in video_only.items():
            fmt['audio_url'] = audio_format_url
            combined[h] = fmt

        formats = sorted(combined.values(), key=lambda x: x.get('height', 0))

        # Fallback
        if not formats and info.get('url'):
            formats = [{'quality': 'Best', 'url': info.get('url'), 'ext': 'mp4', 'needs_merge': False}]

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
    """Merge video+audio for 1080p using ffmpeg"""
    video_url = request.args.get('video_url')
    audio_url = request.args.get('audio_url')
    title     = request.args.get('title', 'video')

    if not video_url or not audio_url:
        return jsonify({"error": "video_url and audio_url required"}), 400

    try:
        # Check ffmpeg available
        subprocess.run(['ffmpeg', '-version'], capture_output=True, check=True)
    except:
        return jsonify({"error": "ffmpeg not available"}), 500

    def generate():
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
            subprocess.run(cmd, capture_output=True)
            with open(out_path, 'rb') as f:
                while chunk := f.read(8192):
                    yield chunk

    filename = title.replace(' ', '_')[:50] + '_1080p.mp4'
    return Response(
        generate(),
        mimetype='video/mp4',
        headers={'Content-Disposition': f'attachment; filename="{filename}"'}
    )


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
    
