"""Which cameras to run, from the CAMERAS / VIDEO_SOURCE settings."""
MAX_CAMERAS = 4
MAX_NAME = 30
DEFAULT_NAME = "Kamera 1"


def parse_cameras(spec: str, single_source: str):
    """'Kirish=0;Sex=http://...' -> [(name, source), ...]. An empty spec means one camera.

    The name identifies the camera: its zones and incidents are stored under it.
    """
    if not spec.strip():
        return [(DEFAULT_NAME, single_source)]
    cameras, names = [], set()
    for part in filter(None, (p.strip() for p in spec.split(";"))):
        name, sep, source = part.partition("=")
        name, source = name.strip(), source.strip()
        if not sep or not name or not source or len(name) > MAX_NAME or "://" in name:
            # The entry is not echoed: it may contain a stream password.
            raise ValueError(f"CAMERAS: har bir kamera 'Nom=manba' ko'rinishida bo'lsin ({len(cameras) + 1}-yozuv)")
        if name.lower() in names:
            raise ValueError(f"CAMERAS: kamera nomi takrorlangan: {name}")
        names.add(name.lower())
        cameras.append((name, source))
    if not 1 <= len(cameras) <= MAX_CAMERAS:
        raise ValueError(f"CAMERAS: 1 dan {MAX_CAMERAS} tagacha kamera")
    return cameras
