import os

# OpenCV and FFmpeg print stream URLs, passwords included, straight to the terminal where Python
# logging cannot filter them. These must be set before cv2 is first imported.
os.environ.setdefault("OPENCV_LOG_LEVEL", "SILENT")
os.environ.setdefault("OPENCV_FFMPEG_LOGLEVEL", "-8")

from .redact import install  # noqa: E402

install()
