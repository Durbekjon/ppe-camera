"""Build a test clip from still photos (slow pan/zoom, 5 s each) so the pipeline can be exercised offline."""
import glob, sys
import cv2

out_path = sys.argv[1] if len(sys.argv) > 1 else "testdata/stills.mp4"
W, H, FPS, SECS = 960, 720, 25, 5
out = cv2.VideoWriter(out_path, cv2.VideoWriter_fourcc(*"mp4v"), FPS, (W, H))
for p in sorted(glob.glob("testdata/images/*.jpg")):
    img = cv2.imread(p)
    s = max(W / img.shape[1], H / img.shape[0]) * 1.15
    img = cv2.resize(img, (int(img.shape[1] * s) + 1, int(img.shape[0] * s) + 1))
    n = FPS * SECS
    for i in range(n):
        x = int((img.shape[1] - W) * i / n)
        y = int((img.shape[0] - H) * 0.2)
        out.write(img[y:y + H, x:x + W])
out.release()
print("wrote", out_path)
