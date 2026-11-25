"""Serve a video file as an MJPEG HTTP stream (like a phone IP-camera app) to test stream sources and drops.

Usage: python tools/fake_camera.py video.mp4 [port]   ->  http://127.0.0.1:8770/video
"""
import sys, time
from http.server import BaseHTTPRequestHandler, HTTPServer
import cv2

path, port = sys.argv[1], int(sys.argv[2]) if len(sys.argv) > 2 else 8770


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "multipart/x-mixed-replace; boundary=frame")
        self.end_headers()
        cap = cv2.VideoCapture(path)
        while True:
            ok, frame = cap.read()
            if not ok:
                cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                continue
            jpg = cv2.imencode(".jpg", frame)[1].tobytes()
            self.wfile.write(b"--frame\r\nContent-Type: image/jpeg\r\nContent-Length: %d\r\n\r\n" % len(jpg) + jpg + b"\r\n")
            time.sleep(0.04)

    def log_message(self, *a):
        pass


HTTPServer(("127.0.0.1", port), Handler).serve_forever()
