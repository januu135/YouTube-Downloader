"""djangoProject URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/3.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from ytdl import views

urlpatterns = [
    path('', views.download_video, name='download_video'),
    path('br/', views.br, name='br'),
    path('fr/', views.fr, name='fr'),
    path('id/', views.id, name='id'),
    path('convert-mp3/', views.convert_to_mp3, name='convert_to_mp3'),
    path('download-stream/', views.download_stream, name='download_stream'),
]
