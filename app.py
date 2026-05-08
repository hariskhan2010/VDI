# DEPLOY TO RAILWAY:
# 1. Push project to GitHub
# 2. railway.app -> New Project -> Deploy from GitHub
# 3. Railway uses nixpacks.toml to install ffmpeg automatically
# 4. Settings -> Networking -> Generate Domain
# 5. Copy domain -> paste in index.html as API_BASE value
# 6. Deploy index.html on netlify.com/drop (free, instant)

import os
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import yt_dlp
from yt_dlp.utils import DownloadError

app = Flask(__name__)
CORS(app)

FRONTEND_DIR = os.path.join(os.path.dirname(__file__), 'frontend')

@app.route('/')
def serve_frontend():
    return send_from_directory(FRONTEND_DIR, 'index.html')

def get_ydl_opts():
    return {
        'format': 'best[ext=mp4]/best[ext=webm]/best',
        'noplaylist': True,
        'nocheckcertificate': True,
        'quiet': True,
        'no_warnings': True,
        'extractor_args': {
            'youtube': {
                'player_client': ['tv_embedded', 'android'],
            }
        },
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Mobile Safari/537.36',
            'Accept-Language': 'en-US,en;q=0.9',
            'Referer': 'https://www.google.com/',
        },
        'retries': 5,
        'fragment_retries': 5,
        'socket_timeout': 30,
    }

def detect_platform(url):
    patterns = {
        'YouTube': ['youtube.com', 'youtu.be'],
        'Facebook': ['facebook.com', 'fb.watch'],
        'Instagram': ['instagram.com'],
        'TikTok': ['tiktok.com', 'vm.tiktok.com'],
        'Twitter/X': ['twitter.com', 'x.com', 't.co'],
        'Vimeo': ['vimeo.com'],
        'Dailymotion': ['dailymotion.com', 'dai.ly'],
        'Reddit': ['reddit.com', 'v.redd.it'],
        'Twitch': ['twitch.tv', 'clips.twitch.tv'],
        'LinkedIn': ['linkedin.com'],
        'Pinterest': ['pinterest.com', 'pin.it'],
        'Snapchat': ['snapchat.com'],
        'Bilibili': ['bilibili.com', 'b23.tv'],
    }
    for platform, domains in patterns.items():
        if any(d in url for d in domains):
            return platform
    return 'Unknown'

def parse_resolution(format_obj):
    height = format_obj.get('height') or 0
    width = format_obj.get('width') or 0
    if height and width:
        return height * width
    return 0

@app.route('/health')
def health():
    return jsonify({"status": "running", "message": "VidSnap API is live"})

@app.route('/info')
def get_info():
    url = request.args.get('url', '')
    
    if not url or not (url.startswith('http://') or url.startswith('https://')):
        return jsonify({"error": "Please provide a valid URL starting with http:// or https://"}), 400
    
    platform = detect_platform(url)
    
    try:
        ydl_opts = get_ydl_opts()
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
    except DownloadError:
        return jsonify({"error": "Could not fetch video. It may be private, age-restricted, or unsupported."}), 400
    except Exception:
        return jsonify({"error": "Server error. Please try again."}), 500
    
    title = info.get('title', 'Unknown')
    thumbnail = info.get('thumbnail', None)
    duration = info.get('duration', 0)
    uploader = info.get('uploader', info.get('channel', info.get('creator', 'Unknown')))
    
    formats = info.get('formats', [])
    filtered_formats = []
    
    for f in formats:
        url_direct = f.get('url')
        if url_direct and url_direct.startswith('http'):
            resolution = ''
            height = f.get('height')
            width = f.get('width')
            if height and width:
                resolution = f'{width}x{height}'
            elif height:
                resolution = f'{height}p'
            else:
                resolution = 'N/A'
            
            quality_label = f'{resolution}' if resolution != 'N/A' else 'N/A'
            filesize = f.get('filesize') or f.get('filesize_approx') or None
            
            filtered_formats.append({
                'format_id': f.get('format_id', 'unknown'),
                'quality': f'{f.get("height", "?")}p' if f.get('height') else 'audio',
                'ext': f.get('ext', 'mp4'),
                'resolution': resolution,
                'url': url_direct,
                'filesize': filesize,
            })
    
    filtered_formats.sort(key=parse_resolution, reverse=True)
    
    best_url = None
    best_format = info.get('url')
    if best_format and best_format.startswith('http'):
        best_url = best_format
    elif filtered_formats:
        best_url = filtered_formats[0]['url']
    
    return jsonify({
        'title': title,
        'thumbnail': thumbnail,
        'duration': duration,
        'uploader': uploader,
        'platform': platform,
        'best_url': best_url,
        'formats': filtered_formats,
    })

@app.route('/supported')
def get_supported():
    platforms = [
        {"name": "YouTube", "emoji": "\u25b6\ufe0f"},
        {"name": "Facebook", "emoji": "\U0001f4d8"},
        {"name": "Instagram", "emoji": "\U0001f4f8"},
        {"name": "TikTok", "emoji": "\U0001f3b5"},
        {"name": "Twitter/X", "emoji": "\U0001f426"},
        {"name": "Vimeo", "emoji": "\U0001f39e\ufe0f"},
        {"name": "Dailymotion", "emoji": "\U0001f3ac"},
        {"name": "Reddit", "emoji": "\U0001f916"},
        {"name": "Twitch", "emoji": "\U0001f49c"},
        {"name": "Pinterest", "emoji": "\U0001f4cc"},
        {"name": "LinkedIn", "emoji": "\U0001f4bc"},
        {"name": "Bilibili", "emoji": "\U0001f4fa"},
        {"name": "Snapchat", "emoji": "\U0001f47b"},
        {"name": "1000+ more", "emoji": "\U0001f310"},
    ]
    return jsonify({"platforms": platforms})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
