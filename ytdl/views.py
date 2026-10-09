from django.shortcuts import render
from django.http import HttpResponse
import yt_dlp as youtube_dl
from .forms import DownloadForm
import re


def get_video_data(video_url):
    """
    Extract YouTube video information using yt-dlp
    and safely handle missing format fields.
    """

    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
    }

    with youtube_dl.YoutubeDL(ydl_opts) as ydl:
        meta = ydl.extract_info(video_url, download=False)

    video_audio_streams = []

    for m in meta.get("formats", []):
        # filesize may not exist in some formats
        file_size = m.get("filesize")

        if file_size is None:
            # Sometimes filesize is available as filesize_approx
            file_size = m.get("filesize_approx")

        if file_size is not None:
            try:
                file_size = f"{round(int(file_size) / 1000000, 2)} MB"
            except (ValueError, TypeError):
                file_size = "Unknown"
        else:
            file_size = "Unknown"

        # Some formats don't have height/width
        height = m.get("height")
        width = m.get("width")

        resolution = "Audio"

        if height is not None:
            if width is not None:
                resolution = f"{height}x{width}"
            else:
                resolution = f"{height}p"

        # URL may not exist in unusual formats
        video_url_stream = m.get("url", "")

        video_audio_streams.append({
            "resolution": resolution,
            "extension": m.get("ext", "Unknown"),
            "file_size": file_size,
            "video_url": video_url_stream,
        })

    # Reverse list so higher quality appears first
    video_audio_streams.reverse()

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
        "streams": video_audio_streams,
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
