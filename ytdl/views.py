from django.shortcuts import render
from django.http import HttpResponse
import os
from django.conf import settings
import yt_dlp as youtube_dl
from .forms import DownloadForm
import re


DEFAULT_COOKIES = """# Netscape HTTP Cookie File
# https://curl.haxx.se/rfc/cookie_spec.html
# This is a generated file! Do not edit.

.youtube.com	TRUE	/	TRUE	1827171625	__Secure-3PAPISID	pEbOLB5KVaMsZk7n/Ahfl0mDU10rTdA_s3
.youtube.com	TRUE	/	TRUE	1827179223	PREF	f4=4000000&tz=Asia.Calcutta
.youtube.com	TRUE	/	FALSE	1827171625	HSID	AyBrwri5RHg2BYPJ9
.youtube.com	TRUE	/	TRUE	1827171625	SSID	AW4Mqtucfz1vWm4aU
.youtube.com	TRUE	/	FALSE	1827171625	APISID	vaIfVq_Be5x4smK_/AVkrWDb_PrLqotnVk
.youtube.com	TRUE	/	TRUE	1827171625	SAPISID	pEbOLB5KVaMsZk7n/Ahfl0mDU10rTdA_s3
.youtube.com	TRUE	/	TRUE	1827171625	__Secure-1PAPISID	pEbOLB5KVaMsZk7n/Ahfl0mDU10rTdA_s3
.youtube.com	TRUE	/	TRUE	1827171620	LOGIN_INFO	AFmmF2swRAIgZo9UFfdBlVZszWVkwv8gpGAdw4Q9slogIxaixJvX9HcCIGUh2DhWaTnK99B9UDUFZpJJpl5tOJ3BrassvC3FjywR:QUQ3MjNmelI1OGgzMkp6RGdCbW5rSklxek5qZ0xHdmJFcXcweW43TmlCdlBnVDNDVjgzWTVKYWMyZW1icV9zWm1UVXNkVC1qSmFKX3pVQ0Y4OUNmQWJiRWp3aUxLbkZfU1ZOczJHejNEcGdsSkdfeUxyaF9uYWZDbENFalgtajVYX250d0FZUTdTeDZGWjdnbzhqZzZzRzJSV1hrV0V4bWNR
.youtube.com	TRUE	/	FALSE	1827171625	SID	g.a000Dwm_hxzKFAxWzFr9x4mXYNa-znqC_SdbU7O91RBxzH8qPQ3tKilgZvSKCqvZHKQu0i8AagACgYKAc8SARMSFQHGX2Mizg2a_6Kn5R10Rk26QONYeRoVAUF8yKrs_yqzPXo3hmp_k1IhWFqo0076
.youtube.com	TRUE	/	TRUE	1827171625	__Secure-1PSID	g.a000Dwm_hxzKFAxWzFr9x4mXYNa-znqC_SdbU7O91RBxzH8qPQ3tpzwi8YVywfcab1iC7HNZkgACgYKAZgSARMSFQHGX2MilC36cveFhCJz6OTocNuFlRoVAUF8yKqDIzcg_cbwEB_Uig__UcNQ0076
.youtube.com	TRUE	/	TRUE	1827171625	__Secure-3PSID	g.a000Dwm_hxzKFAxWzFr9x4mXYNa-znqC_SdbU7O91RBxzH8qPQ3tTLg4EKg3wcbqULYVEikTvgACgYKAYsSARMSFQHGX2MiJpne9XAgKYx1HenYql9P1RoVAUF8yKobVWuVIeqjDydfjd_YIwwj0076
.youtube.com	TRUE	/	TRUE	1824154849	__Secure-1PSIDTS	sidts-CjUBkldj_wsJzBjTvzlvS9A0AqEW3S6e4BubCj12uHW4de8FBKWT_c5VIFzLjpkPg8fvzXJf3RAA
.youtube.com	TRUE	/	TRUE	1824154849	__Secure-3PSIDTS	sidts-CjUBkldj_wsJzBjTvzlvS9A0AqEW3S6e4BubCj12uHW4de8FBKWT_c5VIFzLjpkPg8fvzXJf3RAA
.youtube.com	TRUE	/	FALSE	1824155245	SIDCC	APD_SKEVINpUo3NFgQEXkO5zqGFyBqdrjx4iVakyfCQjRQ8lMzGcYDXJFWMD8_agSiG4G1pLRQ
.youtube.com	TRUE	/	TRUE	1824155245	__Secure-1PSIDCC	APD_SKF2-iny6O0P7LO1wLRdczqUCx7_w9s7UYL9_VPBqYrR76DpoGE9sOy0BYhiU4w7Fqlk
.youtube.com	TRUE	/	TRUE	1824155245	__Secure-3PSIDCC	APD_SKGWY9evY4K6yw-3fY9fzdmVMwSELFB3Jl7DuxhKlomOIcyEf3CNl0Xw0w_rMhnvbDAk
.youtube.com	TRUE	/	TRUE	0	YSC	3VVVjqdAPww
.youtube.com	TRUE	/	TRUE	1808171221	VISITOR_INFO1_LIVE	xlBl4rgXDu8
.youtube.com	TRUE	/	TRUE	1808171221	VISITOR_PRIVACY_METADATA	CgJJThIEGgAgOQ%3D%3D
.youtube.com	TRUE	/	TRUE	1808163615	__Secure-ROLLOUT_TOKEN	CNfSytCfyo_hzQEQ-8DE0-7LlwMYopOM1O7LlwM%3D
.youtube.com	TRUE	/	TRUE	1808163614	__Secure-YNID	CuwBCAUSngEB8QZuZuRCUifaufLcH1aFGW15RJKpz-A4VBhBTzTdjQTdWxBZpu2C94t96rywAnRnKkJhboZoit3Rq-5JkxTaUKMesPI_Io3VXzOAswKOe41S56ZrUb3t_Yqtal21itagZy7dPoTw2rpjUFWaXqShpVfXaSM1LRzUCQCaSeOYBc5UYZyt5hzqRIjlqn87PPgy46mBeqwbND8i7DmO_igFMkUB3qmdTyS09HclH0rVqZ7z4J-yFyR0jYnJYcBba0iYDQu4iYkQn8IHtPd4VmJcL7wUM0AdugevOe3JdtM9NvYLuOB47AM
"""


def get_video_data(video_url):
    """
    Extract YouTube video information using yt-dlp with cookie authentication
    and safely handle formats, audio streams, and missing fields.
    """

    cookies_path = getattr(
        settings, "COOKIES_FILE", os.path.join(settings.BASE_DIR, "cookies.txt")
    )
    if not os.path.isabs(str(cookies_path)):
        cookies_path = os.path.join(settings.BASE_DIR, cookies_path)

    # Auto-create cookies.txt if it does not exist
    if not os.path.exists(cookies_path):
        try:
            with open(cookies_path, "w", encoding="utf-8") as f:
                f.write(DEFAULT_COOKIES.strip() + "\n")
        except Exception as e:
            print("Warning: unable to create cookies file:", e)

    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
    }

    if os.path.exists(cookies_path):
        ydl_opts["cookiefile"] = str(cookies_path)

    with youtube_dl.YoutubeDL(ydl_opts) as ydl:
        meta = ydl.extract_info(video_url, download=False)

    raw_formats = meta.get("formats", [])
    video_streams = []
    audio_streams = []
    seen_video_keys = set()
    seen_audio_keys = set()

    for m in raw_formats:
        # Ignore storyboard and formats without a direct URL
        if m.get("ext") == "mhtml" or m.get("format_note") == "storyboard":
            continue

        video_url_stream = m.get("url", "")
        if not video_url_stream:
            continue

        file_size = m.get("filesize") or m.get("filesize_approx")
        if file_size is not None:
            try:
                file_size_str = f"{round(int(file_size) / (1024 * 1024), 2)} MB"
            except (ValueError, TypeError):
                file_size_str = "Unknown"
        else:
            file_size_str = "Unknown"

        height = m.get("height")
        width = m.get("width")
        ext = m.get("ext", "Unknown")
        vcodec = m.get("vcodec", "none")
        acodec = m.get("acodec", "none")

        is_video = vcodec and vcodec != "none"
        is_audio_only = (not vcodec or vcodec == "none") and acodec and acodec != "none"

        if is_video:
            if height is not None:
                resolution = f"{height}p"
            elif width is not None:
                resolution = f"{width}w"
            else:
                resolution = "Video"

            key = (resolution, ext)
            if key not in seen_video_keys:
                seen_video_keys.add(key)
                video_streams.append({
                    "resolution": resolution,
                    "height": height or 0,
                    "extension": ext,
                    "file_size": file_size_str,
                    "video_url": video_url_stream,
                })
        elif is_audio_only:
            abr = m.get("abr") or 0
            key = (ext, abr)
            if key not in seen_audio_keys:
                seen_audio_keys.add(key)
                audio_streams.append({
                    "extension": ext,
                    "file_size": file_size_str,
                    "video_url": video_url_stream,
                    "abr": abr,
                })

    # Sort video streams from highest resolution to lowest
    video_streams.sort(key=lambda s: s.get("height", 0), reverse=True)

    # Sort audio streams from highest bitrate to lowest
    audio_streams.sort(key=lambda s: s.get("abr", 0), reverse=True)

    # Fallback to all streams if no video streams were categorized
    if not video_streams and not audio_streams:
        for m in raw_formats:
            url = m.get("url", "")
            if not url or m.get("ext") == "mhtml":
                continue
            height = m.get("height")
            video_streams.append({
                "resolution": f"{height}p" if height else "Standard",
                "extension": m.get("ext", "Unknown"),
                "file_size": "Unknown",
                "video_url": url,
            })

    # Get thumbnail safely
    thumbnail = meta.get("thumbnail", "")

    # Get duration safely
    duration = meta.get("duration")
    if duration is not None:
        try:
            duration = round(int(duration) / 60, 2)
        except (ValueError, TypeError):
            duration = 0
    else:
        duration = 0

    # Get views safely
    view_count = meta.get("view_count", 0)
    try:
        views = f"{int(view_count):,}"
    except (ValueError, TypeError):
        views = "0"

    context = {
        "title": meta.get("title", "Unknown Title"),
        "streams": video_streams,
        "stream_audio": audio_streams,
        "description": meta.get("description", ""),
        "likes": meta.get("like_count", 0),
        "dislikes": meta.get("dislike_count", 0),
        "thumb": thumbnail,
        "duration": duration,
        "views": views,
    }

    return context


def is_valid_youtube_url(video_url):
    """
    Check whether the URL looks like a YouTube URL.
    """

    if not video_url:
        return False

    regex = (
        r"^(https?://)?"
        r"((www|m)\.)?"
        r"(youtube\.com|youtu\.be)"
        r"(/.+)?$"
    )

    return re.match(regex, video_url) is not None


def download_video(request):
    form = DownloadForm(request.POST or None)

    if form.is_valid():
        video_url = form.cleaned_data.get("url")

        print("YouTube URL:", video_url)

        if not is_valid_youtube_url(video_url):
            return HttpResponse("Enter correct YouTube URL.")

        try:
            context = get_video_data(video_url)

            # Add form to template context
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

        print("YouTube URL:", video_url)

        if not is_valid_youtube_url(video_url):
            return HttpResponse("Enter correct YouTube URL.")

        try:
            context = get_video_data(video_url)

            context["form"] = form

            return render(request, "br.html", context)

        except Exception as e:
            print("ERROR:", e)

            return HttpResponse(
                f"Unable to fetch video information.<br><br>Error: {str(e)}"
            )

    return render(request, "br.html", {"form": form})


def fr(request):
    form = DownloadForm(request.POST or None)

    if form.is_valid():
        video_url = form.cleaned_data.get("url")

        print("YouTube URL:", video_url)

        if not is_valid_youtube_url(video_url):
            return HttpResponse("Enter correct YouTube URL.")

        try:
            context = get_video_data(video_url)

            context["form"] = form

            return render(request, "fr.html", context)

        except Exception as e:
            print("ERROR:", e)

            return HttpResponse(
                f"Unable to fetch video information.<br><br>Error: {str(e)}"
            )

    return render(request, "fr.html", {"form": form})


def id(request):
    form = DownloadForm(request.POST or None)

    if form.is_valid():
        video_url = form.cleaned_data.get("url")

        print("YouTube URL:", video_url)

        if not is_valid_youtube_url(video_url):
            return HttpResponse("Enter correct YouTube URL.")

        try:
            context = get_video_data(video_url)

            context["form"] = form

            return render(request, "id.html", context)

        except Exception as e:
            print("ERROR:", e)

            return HttpResponse(
                f"Unable to fetch video information.<br><br>Error: {str(e)}"
            )

    return render(request, "id.html", {"form": form})
