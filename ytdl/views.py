from django.shortcuts import render
from django.http import HttpResponse
from pytubefix import YouTube
from .forms import DownloadForm
import re


def is_valid_youtube_url(video_url):
    """
    Check whether the URL looks like a YouTube URL.
    """
    if not video_url:
        return False
    pattern = r"^(https?://)?((www|m)\.)?(youtube\.com|youtu\.be)(/.+)?$"
    return re.match(pattern, video_url) is not None


def get_video_data(video_url):
    """
    Extract YouTube video information using pytubefix.
    Directly retrieves title, author, views, duration, thumbnail,
    and all video/audio streams with download URLs without requiring cookies.
    """
    yt = YouTube(video_url)

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
        if not stream_url:
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

    context = {
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
    return context


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
