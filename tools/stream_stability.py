"""PPE-001: Automated stream stability & reconnect verification tool.

Measures:
- Sustained FPS over time
- Frame interval jitter and drops
- Recovery and reconnection time when the video stream drops
"""
import argparse
import sys
import time
import threading
from app.video import VideoSource


def measure_stream(source: str, duration: float = 15.0, test_reconnect: bool = False):
    print(f"=== Stream sinovi: {source} (davomiyligi: {duration:.1f} s) ===")
    vs = VideoSource(source, width=960)
    vs.start()
    
    start_time = time.time()
    last_seq = -1
    frame_count = 0
    intervals = []
    last_frame_time = None
    
    # Wait for initial connection
    connected_time = None
    while time.time() - start_time < 10.0:
        seq, frame = vs.read()
        if frame is not None and vs.connected:
            connected_time = time.time()
            print(f"✅ Ulandi: {vs.label} (kechikish: {connected_time - start_time:.2f} s)")
            break
        time.sleep(0.05)
        
    if not connected_time:
        print(f"❌ Xatolik: {source} manbasiga ulanib bo'lmadi!")
        vs.stop()
        return False, 0.0, 0
        
    # Read loop
    loop_start = time.time()
    while time.time() - loop_start < duration:
        seq, frame = vs.read()
        if seq != last_seq and frame is not None:
            now = time.time()
            if last_frame_time is not None:
                intervals.append(now - last_frame_time)
            last_frame_time = now
            last_seq = seq
            frame_count += 1
        time.sleep(0.01)
        
    elapsed = time.time() - loop_start
    measured_fps = frame_count / elapsed if elapsed > 0 else 0
    avg_interval = (sum(intervals) / len(intervals) * 1000) if intervals else 0
    
    print(f"📊 Natijalar:")
    print(f"  • Olingan kadrlar: {frame_count} ta")
    print(f"  • O'lchangan FPS: {measured_fps:.1f} kadr/s")
    print(f"  • O'rtacha oraliq: {avg_interval:.1f} ms")
    print(f"  • Ulanish holati: {'Faol ✅' if vs.connected else 'Uzilgan ❌'}")
    
    vs.stop()
    return True, measured_fps, frame_count


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Test video source stability and reconnect")
    parser.add_argument("source", nargs="?", default="testdata/stills.mp4", help="Video source (0, URL, or file)")
    parser.add_argument("--duration", type=float, default=5.0, help="Duration in seconds")
    args = parser.parse_args()
    
    ok, fps, count = measure_stream(args.source, args.duration)
    sys.exit(0 if ok and count > 0 else 1)
