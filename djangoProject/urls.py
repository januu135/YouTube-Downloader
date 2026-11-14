from django.contrib import admin
from django.urls import path
from django.views.generic.base import RedirectView
from django.templatetags.static import static
from django.http import HttpResponse
from django.conf import settings
from ytdl import views
import os

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

def sitemap_view(request):
    sitemap_path = os.path.join(settings.BASE_DIR, "sitemap.xml")
    if os.path.exists(sitemap_path):
        with open(sitemap_path, "r", encoding="utf-8") as f:
            content = f.read()
    else:
        content = '''<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:xhtml="http://www.w3.org/1999/xhtml">
  <url>
       <loc>https://y2-mate.online/</loc>
       <lastmod>2026-11-05T13:31:14+00:00</lastmod>
       <priority>1.0000</priority>
  </url>
  <url>
       <loc>https://y2-mate.online/br/</loc>
       <lastmod>2026-11-05T13:31:14+00:00</lastmod>
       <priority>0.8000</priority>
  </url>
  <url>
       <loc>https://y2-mate.online/fr/</loc>
       <lastmod>2026-11-05T13:31:14+00:00</lastmod>
       <priority>0.8000</priority>
  </url>
  <url>
       <loc>https://y2-mate.online/id/</loc>
       <lastmod>2026-11-05T13:31:14+00:00</lastmod>
       <priority>0.8000</priority>
  </url>
  <url>
       <loc>https://y2-mate.online/terms-and-conditions/</loc>
       <lastmod>2026-11-15T00:00:00+00:00</lastmod>
       <priority>0.5000</priority>
  </url>
  <url>
       <loc>https://y2-mate.online/privacy-policy/</loc>
       <lastmod>2026-11-15T00:00:00+00:00</lastmod>
       <priority>0.5000</priority>
  </url>
</urlset>'''
    return HttpResponse(content, content_type="application/xml")

def robots_view(request):
    content = "User-agent: *\nAllow: /\n\nSitemap: https://y2-mate.online/sitemap.xml\n"
    return HttpResponse(content, content_type="text/plain")

urlpatterns = [
    path('favicon.ico', favicon_view, name='favicon'),
    path('sitemap.xml', sitemap_view, name='sitemap'),
    path('robots.txt', robots_view, name='robots'),
    path('privacy-policy/', views.privacy_policy, name='privacy_policy'),
    path('privacy/', views.privacy_policy, name='privacy'),
    path('terms-and-conditions/', views.terms_and_conditions, name='terms_and_conditions'),
    path('terms-of-service/', views.terms_and_conditions, name='terms_of_service'),
    path('terms/', views.terms_and_conditions, name='terms'),
    path('', views.download_video, name='download_video'),
    path('br/', views.br, name='br'),
    path('fr/', views.fr, name='fr'),
    path('id/', views.id, name='id'),
    path('convert-mp3/', views.convert_to_mp3, name='convert_to_mp3'),
    path('download-stream/', views.download_stream, name='download_stream'),
]
