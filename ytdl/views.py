from django.shortcuts import render
from django.http import HttpResponse
from .forms import DownloadForm
import os
import re
import yt_dlp
from django.conf import settings

try:
    from pytubefix import YouTube
except ImportError:
    YouTube = None


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
    last_err = None

    strategies = [
        # Strategy 1: Standard clean yt-dlp extraction (best compatibility across monetized videos)
        {
            "geo_bypass": True,
        },
        # Strategy 2: Multi-client fallback skipping webpage & embedded configs (bypasses HTML ad injection)
        {
            "geo_bypass": True,
            "extractor_args": {
                "youtube": {
                    "player_client": ["web", "mweb", "android", "ios"],
                    "player_skip": ["webpage", "configs"],
                }
            },
        },
        # Strategy 3: Mobile client API (avoids desktop web ad checkpoints)
        {
            "geo_bypass": True,
            "extractor_args": {
                "youtube": {
                    "player_client": ["android", "ios", "mweb"],
                }
            },
        },
        # Strategy 4: Web embedded & TV client
        {
            "geo_bypass": True,
            "extractor_args": {
                "youtube": {
                    "player_client": ["web_embedded", "tv"],
                }
            },
        },
    ]

    # If a real cookie file exists on disk, append authenticated fallback strategies
    if cookie_path:
        for s in strategies[:2]:
            cs = dict(s)
            cs["cookiefile"] = cookie_path
            strategies.append(cs)

    common_opts = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "nocheckcertificate": True,
        "cachedir": False,
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
            if "available in your country" in err_msg or "country" in err_msg or "unavailable" in err_msg:
                for country in ["US", "GB", "DE", "IN", "JP", "CA", "AU"]:
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

    return {
        "title": meta.get("title", "Unknown Title"),
        "author": meta.get("uploader", ""),
        "streams": video_streams,
        "stream_audio": audio_streams,
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
        "ANDROID",
        "IOS",
        "MWEB",
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
        "title": getattr(yt, "title", "Unknown Title") or "Unknown Title",
        "author": getattr(yt, "author", "") or "",
        "streams": video_streams,
        "stream_audio": audio_streams,
        "description": getattr(yt, "description", "") or "",
        "likes": 0,
        "dislikes": 0,
        "thumb": getattr(yt, "thumbnail_url", "") or "",
        "duration": duration,
        "views": views,
    }


def get_video_data(video_url):
    """
    Extract YouTube video information.
    Prioritizes yt-dlp which reliably handles monetized and ad-bearing videos.
    Falls back to pytubefix if needed.
    """
    errors = []

    # 1. Primary: yt-dlp with multi-client & ad-bypass strategies
    try:
        return extract_with_ytdlp(video_url)
    except Exception as e:
        print("yt-dlp extraction failed:", e)
        errors.append(f"yt-dlp: {e}")

    # 2. Fallback: pytubefix
    try:
        return extract_with_pytubefix(video_url)
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
