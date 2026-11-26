from app import config


def test_dotenv_ignores_notes_after_a_value(tmp_path, monkeypatch):
    env = tmp_path / ".env"
    env.write_text("A_FLAG=1        # also alert\nA_URL=rtsp://u:p#w@h/s\nA_QUOTED=\"x # y\"\n# A_OFF=1\n")
    for key in ("A_FLAG", "A_URL", "A_QUOTED", "A_OFF"):
        monkeypatch.delenv(key, raising=False)
    config._load_dotenv(env)
    import os
    assert os.environ["A_FLAG"] == "1"
    assert os.environ["A_URL"] == "rtsp://u:p#w@h/s"  # a '#' inside a value stays
    assert os.environ["A_QUOTED"] == "x # y"
    assert "A_OFF" not in os.environ
