"""
Launch script for Human-in-the-Loop Labeling Tool
Web frontend only (fastest option)
"""
import subprocess
import sys
import os

# Suppress ffmpeg/libav warnings BEFORE any imports
os.environ["OPENCV_LOG_LEVEL"] = "SILENT"
os.environ["OPENCV_FFMPEG_LOGLEVEL"] = "-8"
os.environ["OPENCV_VIDEOIO_DEBUG"] = "0"
os.environ["OPENCV_FFMPEG_DEBUG"] = "0"
os.environ["FFREPORT"] = ""  # Disable ffmpeg report
os.environ["AV_LOG_FORCE_NOCOLOR"] = "1"

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def main():
    print("=" * 60)
    print("Human-in-the-Loop Labeling Tool")
    print("=" * 60)
    print()
    print("Backend API: http://localhost:8000")
    print("API Docs:    http://localhost:8000/docs")
    print("Web UI:      http://localhost:8000/web/index.html")
    print()
    print("For remote access (ngrok):")
    print("  1. Open another terminal")
    print("  2. Run: ngrok http 8000")
    print("  3. Share the ngrok URL + /web/index.html")
    print()
    print("Press Ctrl+C to stop")
    print("=" * 60)

    subprocess.run([
        sys.executable, "-m", "uvicorn",
        "backend.main:app",
        "--host", "0.0.0.0",
        "--port", "8000",
        "--reload"
    ])


if __name__ == "__main__":
    main()
