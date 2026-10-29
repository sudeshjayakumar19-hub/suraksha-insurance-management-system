import os

# Render injects PORT dynamically (defaults to 5000 for local runs)
port = os.environ.get("PORT", "5000")
bind = f"0.0.0.0:{port}"

# Concurrency tuning suitable for Render's free tier (512MB RAM)
workers = int(os.environ.get("WEB_CONCURRENCY", 2))
threads = int(os.environ.get("PYTHON_THREADS", 4))
timeout = 120
keepalive = 5

accesslog = "-"
errorlog = "-"
loglevel = "info"
