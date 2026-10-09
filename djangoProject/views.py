from django.shortcuts import render

def download_video(request):
    return render (request,'download_video.html')

def br(request):
    return render (request,'br.html')