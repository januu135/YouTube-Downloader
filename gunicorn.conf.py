"""
Gunicorn configuration for YouTube-Downloader production deployment.
Optimized for high-concurrency video downloading, media conversion,
and preventing worker starvation / timeout (502 Bad Gateway).
"""
import multiprocessing
import os

# Server socket
bind = os.environ.get("GUNICORN_BIND", "127.0.0.1:8000")
backlog = 2048

# Worker processes
# Calculate workers: 2-4 workers or dynamic based on CPU cores
cpu_count = multiprocessing.cpu_count()
workers = int(os.environ.get("GUNICORN_WORKERS", max(2, min(cpu_count * 2, 4))))

# Use gthread worker class so multiple slow streaming/conversion requests
# do not starve all Gunicorn worker processes.
worker_class = "gthread"
threads = int(os.environ.get("GUNICORN_THREADS", 4))
worker_connections = 1000

# Timeout: Allow long video conversion and streaming downloads without
# premature worker killing by Gunicorn supervisor which causes 502 Bad Gateway.
timeout = int(os.environ.get("GUNICORN_TIMEOUT", 300))
graceful_timeout = 30
keepalive = 5

# Memory management & recycling
# Automatically restart workers after serving requests to prevent memory leaks from yt-dlp/ffmpeg
max_requests = 1000
max_requests_jitter = 100

# Logging
accesslog = "-"
errorlog = "-"
loglevel = "info"

# Process naming
proc_name = "youtube_downloader_gunicorn"
