"""Person ID assignment with ByteTrack (motion prediction keeps IDs stable better than plain box overlap)."""
from types import SimpleNamespace

import numpy as np
from ultralytics.engine.results import Boxes
from ultralytics.trackers.byte_tracker import BYTETracker

# Frames a lost person is remembered (4 s at 30 FPS).
BUFFER_FRAMES = 120


class PersonTracker:
    def __init__(self, min_conf: float = 0.4):
        self._tracker = BYTETracker(
            SimpleNamespace(
                track_high_thresh=min_conf,
                track_low_thresh=0.1,
                new_track_thresh=min_conf,  # every accepted person may start a track
                track_buffer=BUFFER_FRAMES,
                match_thresh=0.9,
                fuse_score=True,
            )
        )

    def update(self, persons):
        """Return [(track id, detection), ...] for the people matched in this frame."""
        rows = np.array([[*p.box, p.conf, 0] for p in persons], np.float32).reshape(-1, 6)
        # The image shape is required by Boxes but not used for pixel xyxy input.
        result = self._tracker.update(Boxes(rows, (1, 1)))
        return [(int(r[4]), persons[int(r[-1])]) for r in result]
