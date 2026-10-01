#!/bin/bash
set -e

# Khởi động Xvfb virtual display
Xvfb :99 -screen 0 1280x900x24 -ac +extension GLX +render -noreset &
export DISPLAY=:99

# Chạy ứng dụng web server + bot
exec python3 app.py
