from django.contrib import admin
from django.urls import path
from django.views.generic.base import RedirectView
from django.templatetags.static import static
from django.http import HttpResponse
from ytdl import views

def favicon_view(request):
    svg = '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" width="64" height="64">
  <defs>
    <linearGradient id="grad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#ff3b30"/>
      <stop offset="100%" stop-color="#e02828"/>
    </linearGradient>
  </defs>
  <rect width="64" height="64" rx="16" fill="url(#grad)"/>
  <path d="M26 20 L44 32 L26 44 Z" fill="#ffffff"/>
  <path d="M22 48 L42 48" stroke="#ffffff" stroke-width="4" stroke-linecap="round"/>
</svg>'''
    return HttpResponse(svg, content_type="image/svg+xml")

urlpatterns = [
    path('favicon.ico', favicon_view, name='favicon'),
    path('', views.download_video, name='download_video'),
    path('br/', views.br, name='br'),
    path('fr/', views.fr, name='fr'),
    path('id/', views.id, name='id'),
    path('convert-mp3/', views.convert_to_mp3, name='convert_to_mp3'),
    path('download-stream/', views.download_stream, name='download_stream'),
]
