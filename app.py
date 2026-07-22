"""
Entry point for Render deployment.

Render's free "Web Service" tier requires the process to bind to a port
and respond to HTTP requests (used for health checks). Telegram bots
normally just poll Telegram's servers and don't need a web server, so
this file runs a tiny Flask app in a background thread purely to satisfy
that requirement, while the actual bot runs via long-polling.
"""

import os
import threading
import logging

from flask import Flask

from bot import run_bot

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)


@app.route("/")
def index():
    return "Bot is alive and polling Telegram for updates."


def start_web_server():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)


if __name__ == "__main__":
    web_thread = threading.Thread(target=start_web_server, daemon=True)
    web_thread.start()
    run_bot()
