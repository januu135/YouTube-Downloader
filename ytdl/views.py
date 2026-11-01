from django.shortcuts import render
from django.http import HttpResponse, FileResponse, StreamingHttpResponse
import tempfile
import glob
import time
import sys
import subprocess
import requests
from .forms import DownloadForm
import os
import re
import yt_dlp
from django.conf import settings
from django.core.cache import cache

try:
    from pytubefix import YouTube
except ImportError:
    YouTube = None


def extract_video_id(video_url):
    """
    Extract canonical 11-char YouTube video ID.
    Supports youtu.be, youtube.com/watch?v=, youtube.com/shorts/, youtube.com/embed/, etc.
    """
    if not video_url:
        return None
    patterns = [
        r"(?:v=|/v/|youtu\.be/|/embed/|/shorts/)([a-zA-Z0-9_-]{11})",
    ]
    for pattern in patterns:
        match = re.search(pattern, video_url.strip())
        if match:
            return match.group(1)
    return None


def is_valid_youtube_url(video_url):
    """
    Check whether the URL looks like a YouTube URL.
    """
    if not video_url:
        return False
    pattern = r"^(https?://)?((www|m|music)\.)?(youtube\.com|youtu\.be)(/.+)?$"
    return re.match(pattern, video_url.strip()) is not None


def get_cookie_file():
    """
    Returns path to a valid cookies.txt file if it exists on disk, else None.
    Avoids injecting expired default cookies into global openers.
    """
    base_dir = str(settings.BASE_DIR) if getattr(settings, "configured", False) and hasattr(settings, "BASE_DIR") else ""
    cookie_candidates = [
        os.path.join(base_dir, "cookies.txt") if base_dir else "",
        os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "cookies.txt"),
        "/var/www/YouTube-Downloader/cookies.txt",
    ]
    for p in cookie_candidates:
        if p and os.path.exists(p) and os.path.getsize(p) > 50:
            return p
    return None


def extract_with_ytdlp(video_url):
    """
    Primary extraction engine using yt-dlp with multi-strategy fallbacks.
    Bypasses YouTube ad-insertion, bot-checks, and SABR restrictions
    on monetized and ad-bearing videos.
    """
    cookie_path = get_cookie_file()
    print(f"[yt-dlp] Cookie file detected: {cookie_path}")
    last_err = None

    base_strategies = [
        # Strategy 1: TV & TV embedded clients (most resilient against bot-check blocks on datacenter IPs)
        {
            "geo_bypass": True,
            "extractor_args": {
                "youtube": {
                    "player_client": ["tv", "tv_embedded"],
                }
            },
        },
        # Strategy 2: Mobile client API (ios, mweb bypass desktop web bot checks)
        {
            "geo_bypass": True,
            "extractor_args": {
                "youtube": {
                    "player_client": ["ios", "mweb", "android"],
                }
            },
        },
        # Strategy 3: Multi-client fallback skipping webpage & embedded configs
        {
            "geo_bypass": True,
            "extractor_args": {
                "youtube": {
                    "player_client": ["web_embedded", "mweb", "ios"],
                    "player_skip": ["webpage", "configs"],
                }
            },
        },
        # Strategy 4: Standard clean yt-dlp extraction
        {
            "geo_bypass": True,
        },
    ]

    strategies = []
    # If a real cookie file exists on disk, prioritize authenticated strategies FIRST
    if cookie_path:
        for s in base_strategies:
            cs = dict(s)
            cs["cookiefile"] = cookie_path
            strategies.append(cs)

    # Append unauthenticated strategies as fallback
    strategies.extend(base_strategies)

    common_opts = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "nocheckcertificate": True,
        "cachedir": False,
        "socket_timeout": 8,
        "getcomments": False,
        "writesubtitles": False,
        "writeautomaticsub": False,
        "extract_flat": False,
        "lazy_playlist": True,
        "no_color": True,
    }

    meta = None
    for strat in strategies:
        try:
            opts = dict(common_opts)
            opts.update(strat)
            with yt_dlp.YoutubeDL(opts) as ydl:
                meta = ydl.extract_info(video_url, download=False)
            if meta and meta.get("formats"):
                break
        except Exception as e:
            last_err = e
            err_msg = str(e).lower()
            if ("not available in your country" in err_msg or "blocked it in your country" in err_msg) and "152" not in err_msg:
                for country in ["US", "GB", "DE", "IN"]:
                    try:
                        retry_opts = dict(common_opts)
                        retry_opts.update(strat)
                        retry_opts["geo_bypass_country"] = country
                        with yt_dlp.YoutubeDL(retry_opts) as ydl:
                            meta = ydl.extract_info(video_url, download=False)
                        if meta and meta.get("formats"):
                            break
                    except Exception as inner_e:
                        last_err = inner_e
                        continue
                if meta and meta.get("formats"):
                    break

    if not meta:
        raise last_err or RuntimeError("yt-dlp could not extract video.")

    raw_formats = meta.get("formats", [])
    video_streams = []
    audio_streams = []
    seen_video_keys = set()
    seen_audio_keys = set()

    for m in raw_formats:
        # Ignore storyboard images (sb0, sb1) and mhtml
        if m.get("ext") == "mhtml" or m.get("format_note") == "storyboard":
            continue

        vurl = m.get("url", "")
        # Require a valid direct playable/downloadable URL (skip m3u8/manifest links)
        if not vurl or "manifest" in vurl or vurl.endswith(".m3u8"):
            continue

        file_size = m.get("filesize") or m.get("filesize_approx")
        if file_size:
            try:
                file_size_str = f"{round(int(file_size) / (1024 * 1024), 2)} MB"
            except Exception:
                file_size_str = "Unknown"
        else:
            file_size_str = "Unknown"

        height = m.get("height")
        width = m.get("width")
        ext = m.get("ext", "mp4")
        vcodec = m.get("vcodec", "none")
        acodec = m.get("acodec", "none")

        is_video = vcodec and vcodec != "none"
        is_audio = (not vcodec or vcodec == "none") and acodec and acodec != "none"
        is_progressive = is_video and acodec and acodec != "none"

        if is_video:
            res_label = f"{height}p" if height else (f"{width}w" if width else "Video")
            key = (res_label, ext, is_progressive)
            if key not in seen_video_keys:
                seen_video_keys.add(key)
                video_streams.append({
                    "format_id": m.get("format_id", ""),
                    "resolution": res_label,
                    "height": height or 0,
                    "is_progressive": 1 if is_progressive else 0,
                    "extension": ext,
                    "file_size": file_size_str,
                    "video_url": vurl,
                })
        elif is_audio:
            abr = m.get("abr") or 0
            key = (ext, abr)
            if key not in seen_audio_keys:
                seen_audio_keys.add(key)
                audio_streams.append({
                    "format_id": m.get("format_id", ""),
                    "resolution": f"{int(abr)} kbps" if abr else "Audio",
                    "extension": ext,
                    "file_size": file_size_str,
                    "video_url": vurl,
                })

    # Sort video streams: progressive streams with sound first, then highest resolution
    video_streams.sort(key=lambda s: (s.get("is_progressive", 0), s.get("height", 0)), reverse=True)

    # Fallback if no streams were classified as video
    if not video_streams and audio_streams:
        video_streams = list(audio_streams)

    duration = meta.get("duration") or 0
    try:
        duration = round(int(duration) / 60, 2)
    except Exception:
        duration = 0

    view_count = meta.get("view_count", 0)
    try:
        views = f"{int(view_count):,}"
    except Exception:
        views = "0"

    # Add MP3 converter format option at the top of audio streams
    audio_streams_with_mp3 = [
        {
            "format_id": "mp3-320",
            "resolution": "320 kbps (High Quality)",
            "extension": "mp3",
            "file_size": "MP3 Audio",
            "is_mp3": True,
            "abr": "320k",
            "video_url": audio_streams[0]["video_url"] if audio_streams else "",
        },
        {
            "format_id": "mp3-192",
            "resolution": "192 kbps (Standard)",
            "extension": "mp3",
            "file_size": "MP3 Audio",
            "is_mp3": True,
            "abr": "192k",
            "video_url": audio_streams[0]["video_url"] if audio_streams else "",
        },
    ] + audio_streams

    return {
        "id": meta.get("id", "") or extract_video_id(video_url) or "",
        "title": meta.get("title", "Unknown Title"),
        "author": meta.get("uploader", ""),
        "streams": video_streams,
        "stream_audio": audio_streams_with_mp3,
        "description": meta.get("description", ""),
        "likes": meta.get("like_count", 0),
        "dislikes": meta.get("dislike_count", 0),
        "thumb": meta.get("thumbnail", ""),
        "duration": duration,
        "views": views,
    }


def extract_with_pytubefix(video_url):
    """
    Secondary fallback extraction engine using pytubefix.
    """
    if YouTube is None:
        raise RuntimeError("pytubefix not installed")

    video_url = video_url.strip()
    yt = None
    last_err = None

    client_candidates = [
        "ANDROID_VR",
        "IOS",
        "MWEB",
        "ANDROID",
        "WEB",
    ]

    for client_name in client_candidates:
        try:
            candidate_yt = YouTube(video_url, client=client_name)
            _ = candidate_yt.streams
            yt = candidate_yt
            break
        except Exception as e:
            last_err = e
            continue

    if yt is None:
        raise last_err or RuntimeError("Pytubefix could not extract video.")

    video_streams = []
    audio_streams = []
    seen_video_keys = set()
    seen_audio_keys = set()

    for stream in yt.streams:
        ext = getattr(stream, "subtype", "mp4") or "mp4"

        filesize = getattr(stream, "filesize", None) or getattr(stream, "filesize_approx", None)
        if filesize:
            try:
                file_size_str = f"{round(int(filesize) / (1024 * 1024), 2)} MB"
            except Exception:
                file_size_str = "Unknown"
        else:
            file_size_str = "Unknown"

        stream_url = getattr(stream, "url", None)
        if not stream_url or "manifest" in stream_url or stream_url.endswith(".m3u8"):
            continue

        resolution = getattr(stream, "resolution", None)
        if resolution:
            key = (resolution, ext)
            if key not in seen_video_keys:
                seen_video_keys.add(key)
                res_num = 0
                try:
                    res_num = int(re.sub(r"\D", "", resolution) or 0)
                except Exception:
                    pass
                video_streams.append({
                    "resolution": resolution,
                    "height": res_num,
                    "is_progressive": 1,
                    "extension": ext,
                    "file_size": file_size_str,
                    "video_url": stream_url,
                })
        else:
            abr = getattr(stream, "abr", "") or ""
            key = (ext, abr)
            if key not in seen_audio_keys:
                seen_audio_keys.add(key)
                audio_streams.append({
                    "resolution": abr or "Audio",
                    "extension": ext,
                    "file_size": file_size_str,
                    "video_url": stream_url,
                })

    video_streams.sort(key=lambda s: s.get("height", 0), reverse=True)

    duration = 0
    if getattr(yt, "length", None):
        try:
            duration = round(int(yt.length) / 60, 2)
        except Exception:
            duration = 0

    views = "0"
    if getattr(yt, "views", None):
        try:
            views = f"{int(yt.views):,}"
        except Exception:
            views = "0"

    return {
        "id": getattr(yt, "video_id", "") or extract_video_id(video_url) or "",
        "title": getattr(yt, "title", "Unknown Title") or "Unknown Title",
        "author": getattr(yt, "author", "") or "",
        "streams": video_streams,
        "stream_audio": audio_streams_with_mp3,
        "description": getattr(yt, "description", "") or "",
        "likes": 0,
        "dislikes": 0,
        "thumb": getattr(yt, "thumbnail_url", "") or "",
        "duration": duration,
        "views": views,
    }


def get_video_data(video_url):
    """
    Extract YouTube video information with in-memory caching and URL normalization.
    Prioritizes yt-dlp which reliably handles monetized and ad-bearing videos.
    Falls back to pytubefix if needed.
    """
    video_id = extract_video_id(video_url)
    cache_key = f"yt_meta_{video_id}" if video_id else None
    if cache_key:
        cached_data = cache.get(cache_key)
        if cached_data:
            print(f"[Cache Hit] Returning cached metadata for video ID: {video_id}")
            return dict(cached_data)

    clean_url = f"https://www.youtube.com/watch?v={video_id}" if video_id else video_url.strip()
    errors = []

    # 1. Primary: yt-dlp with multi-client & ad-bypass strategies
    try:
        data = extract_with_ytdlp(clean_url)
        if cache_key and data:
            cache.set(cache_key, data, timeout=1800)
        return data
    except Exception as e:
        print("yt-dlp extraction failed:", e)
        errors.append(f"yt-dlp: {e}")

    # 2. Fallback: pytubefix
    try:
        data = extract_with_pytubefix(clean_url)
        if cache_key and data:
            cache.set(cache_key, data, timeout=1800)
        return data
    except Exception as e:
        print("pytubefix extraction failed:", e)
        errors.append(f"pytubefix: {e}")

    raise RuntimeError(" | ".join(errors))


def download_video(request):
    form = DownloadForm(request.POST or None)
    if form.is_valid():
        video_url = form.cleaned_data.get("url")
        print("YouTube URL:", video_url)

        if not is_valid_youtube_url(video_url):
            return HttpResponse("Enter correct YouTube URL.")

        try:
            context = get_video_data(video_url)
            context["form"] = form
            return render(request, "home.html", context)
        except Exception as e:
            print("ERROR:", e)
            return HttpResponse(
                f"Unable to fetch video information.<br><br>Error: {str(e)}"
            )

    return render(request, "home.html", {"form": form})


def br(request):
    form = DownloadForm(request.POST or None)
    if form.is_valid():
        video_url = form.cleaned_data.get("url")
        if not is_valid_youtube_url(video_url):
            return HttpResponse("Enter correct YouTube URL.")
        try:
            context = get_video_data(video_url)
            context["form"] = form
            return render(request, "br.html", context)
        except Exception as e:
            return HttpResponse(f"Unable to fetch video information.<br><br>Error: {str(e)}")
    return render(request, "br.html", {"form": form})


def fr(request):
    form = DownloadForm(request.POST or None)
    if form.is_valid():
        video_url = form.cleaned_data.get("url")
        if not is_valid_youtube_url(video_url):
            return HttpResponse("Enter correct YouTube URL.")
        try:
            context = get_video_data(video_url)
            context["form"] = form
            return render(request, "fr.html", context)
        except Exception as e:
            return HttpResponse(f"Unable to fetch video information.<br><br>Error: {str(e)}")
    return render(request, "fr.html", {"form": form})


def id(request):
    form = DownloadForm(request.POST or None)
    if form.is_valid():
        video_url = form.cleaned_data.get("url")
        if not is_valid_youtube_url(video_url):
            return HttpResponse("Enter correct YouTube URL.")
        try:
            context = get_video_data(video_url)
            context["form"] = form
            return render(request, "id.html", context)
        except Exception as e:
            return HttpResponse(f"Unable to fetch video information.<br><br>Error: {str(e)}")
    return render(request, "id.html", {"form": form})


DOWNLOAD_DIR = os.path.join(tempfile.gettempdir(), 'ytdl_downloads')
os.makedirs(DOWNLOAD_DIR, exist_ok=True)


def cleanup_old_downloads():
    """Clean up files in DOWNLOAD_DIR older than 1 hour to prevent disk bloat."""
    try:
        now = time.time()
        for f in os.listdir(DOWNLOAD_DIR):
            fpath = os.path.join(DOWNLOAD_DIR, f)
            if os.path.isfile(fpath) and (now - os.path.getmtime(fpath)) > 3600:
                try:
                    os.remove(fpath)
                except Exception:
                    pass
    except Exception:
        pass


def convert_to_mp3(request):
    """
    Direct MP3 conversion using yt-dlp native audio extraction.
    Downloads, merges, and converts using FFmpeg on disk to ensure valid headers,
    then serves complete, non-corrupt MP3 with FileResponse.
    """
    video_id = request.GET.get('v')
    title = request.GET.get('title', 'audio')
    abr = request.GET.get('abr', '192k')

    if not video_id:
        return HttpResponse("Missing video id parameter 'v'", status=400)

    cleanup_old_downloads()

    cookie_path = get_cookie_file()
    safe_title = re.sub(r'[^\w\s-]', '', title).strip() or 'audio'
    video_url = f"https://www.youtube.com/watch?v={video_id}"
    
    target_pattern = os.path.join(DOWNLOAD_DIR, f"{video_id}_{abr}.mp3")

    if not os.path.exists(target_pattern) or os.path.getsize(target_pattern) < 1000:
        ytdl_cmd = [
            sys.executable, '-m', 'yt_dlp',
            '--no-warnings',
            '--quiet',
            '--force-ipv4',
            '--geo-bypass',
            '--extractor-args', 'youtube:player_client=ios,mweb,android,tv',
            '--concurrent-fragments', '4',
            '-f', 'ba[ext=m4a]/ba[ext=webm]/ba/ba*/18/b/best',
            '-x',
            '--audio-format', 'mp3',
            '--audio-quality', abr,
            '--postprocessor-args', 'ffmpeg:-threads 0',
            '-o', os.path.join(DOWNLOAD_DIR, f"{video_id}_{abr}.%(ext)s"),
        ]
        if cookie_path:
            ytdl_cmd.extend(['--cookies', cookie_path])
        ytdl_cmd.append(video_url)

        try:
            res = subprocess.run(ytdl_cmd, capture_output=True, text=True, timeout=120)
            if res.returncode != 0:
                print(f"[yt-dlp MP3 error] {res.stderr}")
                return HttpResponse(f"MP3 conversion error: {res.stderr or 'Failed to download'}", status=500)
        except Exception as e:
            return HttpResponse(f"Conversion error: {e}", status=500)

    # Find the generated mp3 file
    candidates = glob.glob(os.path.join(DOWNLOAD_DIR, f"{video_id}_{abr}*.mp3"))
    if not candidates or os.path.getsize(candidates[0]) < 1000:
        return HttpResponse("MP3 conversion failed (empty file generated)", status=500)

    filepath = candidates[0]
    return FileResponse(open(filepath, 'rb'), content_type='audio/mpeg', as_attachment=True, filename=f"{safe_title}.mp3")


def download_stream(request):
    """
    Direct video download using yt-dlp native download.
    Downloads and finalizes MP4 container on disk with complete headers,
    then serves full, playable video with FileResponse.
    """
    video_id = request.GET.get('v')
    fid = request.GET.get('fid')
    ext = request.GET.get('ext', 'mp4')
    title = request.GET.get('title', 'video')

    if not video_id:
        return HttpResponse("Missing video id parameter 'v'", status=400)

    cleanup_old_downloads()

    cookie_path = get_cookie_file()
    safe_title = re.sub(r'[^\w\s-]', '', title).strip() or 'video'
    video_url = f"https://www.youtube.com/watch?v={video_id}"

    fid_clean = re.sub(r'[^\w-]', '', fid) if fid else 'best'
    target_base = os.path.join(DOWNLOAD_DIR, f"{video_id}_{fid_clean}")
    
    candidates = glob.glob(f"{target_base}.*")
    valid_file = None
    for c in candidates:
        if os.path.exists(c) and os.path.getsize(c) > 5000:
            valid_file = c
            break

    if not valid_file:
        format_spec = f"{fid}+ba/b[ext=mp4]/{fid}/18/best" if (fid and fid != 'None') else "18/best[ext=mp4]/best"
        ytdl_cmd = [
            sys.executable, '-m', 'yt_dlp',
            '--no-warnings',
            '--quiet',
            '--force-ipv4',
            '--geo-bypass',
            '--extractor-args', 'youtube:player_client=ios,mweb,android,tv',
            '--concurrent-fragments', '4',
            '-f', format_spec,
            '--merge-output-format', 'mp4',
            '-o', f"{target_base}.%(ext)s",
        ]
        if cookie_path:
            ytdl_cmd.extend(['--cookies', cookie_path])
        ytdl_cmd.append(video_url)

        try:
            res = subprocess.run(ytdl_cmd, capture_output=True, text=True, timeout=120)
            if res.returncode != 0:
                print(f"[yt-dlp Video error] {res.stderr}")
                return HttpResponse(f"Video download error: {res.stderr or 'Failed to download'}", status=500)
        except Exception as e:
            return HttpResponse(f"Streaming error: {e}", status=500)

        candidates = glob.glob(f"{target_base}.*")
        for c in candidates:
            if os.path.exists(c) and os.path.getsize(c) > 5000:
                valid_file = c
                break

    if not valid_file:
        return HttpResponse("Video download failed (file could not be finalized)", status=500)

    actual_ext = valid_file.split('.')[-1]
    content_type = f'video/{actual_ext}' if actual_ext != 'mp3' else 'audio/mpeg'
    return FileResponse(open(valid_file, 'rb'), content_type=content_type, as_attachment=True, filename=f"{safe_title}.{actual_ext}")
