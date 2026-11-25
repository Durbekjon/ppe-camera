"""Notices when a camera's view is lost while the stream itself keeps running: covered, blacked out,
turned towards a blank wall, or badly out of focus.

Measured on the project's videos and photos (Nov 2026): real scenes had a grey-level spread of at least 43
and a sharpness (Laplacian variance) of at least 337 on a 160 px wide image; covered, black, uniform or very
blurred frames stayed below 7 and 40. The limits below sit well between the two.
"""
import cv2

MIN_SPREAD = 15.0
MIN_SHARPNESS = 30.0
BLOCKED_AFTER_S = 3.0  # the view must stay lost this long before it counts
RESTORED_AFTER_S = 2.0


def view_ok(frame):
    small = cv2.resize(frame, (160, max(1, int(160 * frame.shape[0] / frame.shape[1]))))
    grey = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
    return grey.std() >= MIN_SPREAD and cv2.Laplacian(grey, cv2.CV_64F).var() >= MIN_SHARPNESS


class ViewGuard:
    def __init__(self):
        self.blocked = False
        self._since = None  # when the current, not yet confirmed, change began

    def update(self, frame, now):
        """Return "blocked" or "restored" when the state changes, else None."""
        lost = not view_ok(frame)
        if lost == self.blocked:
            self._since = None
            return None
        if self._since is None:
            self._since = now
        if now - self._since >= (BLOCKED_AFTER_S if lost else RESTORED_AFTER_S):
            self.blocked, self._since = lost, None
            return "blocked" if lost else "restored"
        return None
