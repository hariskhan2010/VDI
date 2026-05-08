from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import yt_dlp
from yt_dlp.utils import DownloadError

# Vercel has a read-only filesystem — force yt-dlp cache to /tmp
os.environ.setdefault('HOME', '/tmp')
os.environ.setdefault('XDG_CACHE_HOME', '/tmp/.cache')
os.environ.setdefault('YTDLP_CACHE_DIR', '/tmp/.cache/yt-dlp')

app = Flask(__name__)
CORS(app)

def get_ydl_opts():
    return {
        'format': 'best[ext=mp4]/best[ext=webm]/best',
        'noplaylist': True,
        'nocheckcertificate': True,
        'quiet': True,
        'no_warnings': True,
        'age_limit': None,
        'extractor_args': {
            'youtube': {
                'player_client': ['web_creator', 'web', 'android', 'tv_embedded'],
                'skip': ['dash', 'hls'],
            }
        },
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Mobile Safari/537.36',
            'Accept-Language': 'en-US,en;q=0.9',
            'Referer': 'https://www.google.com/',
        },
        'retries': 10,
        'fragment_retries': 10,
        'socket_timeout': 60,
        'extractor_retries': 5,
        'sleep_interval': 1,
        'max_sleep_interval': 5,
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

@app.route('/api/health')
def health():
    return jsonify({"status": "running", "message": "VidSnap API is live"})

@app.route('/api/info')
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

@app.route('/api/supported')
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
