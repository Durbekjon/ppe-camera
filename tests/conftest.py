import pytest

from app import alerts, dataset


@pytest.fixture(autouse=True)
def _keep_tests_away_from_real_data(tmp_path, monkeypatch):
    # The clean-up thread deletes expired files: it must never run against the real data folders.
    monkeypatch.setattr(dataset, "RAW", tmp_path / "raw")
    monkeypatch.setattr(dataset, "EXPORTS", tmp_path / "exports")


@pytest.fixture(autouse=True)
def _stop_sender_threads():
    yield
    # The queue is in the database: a sender left over from one test would deliver the next test's alerts.
    for manager in list(alerts._managers):
        manager.close()
