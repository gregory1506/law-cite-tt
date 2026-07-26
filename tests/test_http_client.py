from unittest.mock import MagicMock, patch

import pytest
import requests

from scraper.http_client import RateLimitedClient


def test_enforces_minimum_delay_between_requests():
    fake_time = [0.0]
    sleeps = []

    def fake_sleep(seconds):
        sleeps.append(seconds)
        fake_time[0] += seconds

    def fake_monotonic():
        return fake_time[0]

    client = RateLimitedClient(
        delay_seconds=1.5, sleep_fn=fake_sleep, time_fn=fake_monotonic
    )

    with patch.object(requests.Session, "get") as mock_get:
        mock_get.return_value = MagicMock(status_code=200)
        client.get("https://example.com/a")
        fake_time[0] += 0.1  # simulate 0.1s passing before the next call
        client.get("https://example.com/b")

    # first call: no prior request, so no sleep for rate limiting.
    # second call: only 0.1s elapsed, so it must sleep ~1.4s to reach 1.5s.
    assert sleeps == [pytest.approx(1.4, abs=0.01)]


def test_retries_on_server_error_then_succeeds():
    client = RateLimitedClient(delay_seconds=0, max_retries=3, sleep_fn=lambda s: None)
    with patch.object(requests.Session, "get") as mock_get:
        mock_get.side_effect = [
            MagicMock(status_code=500),
            MagicMock(status_code=200),
        ]
        response = client.get("https://example.com/a")

    assert response.status_code == 200
    assert mock_get.call_count == 2


def test_raises_after_exhausting_retries_on_repeated_server_errors():
    client = RateLimitedClient(delay_seconds=0, max_retries=2, sleep_fn=lambda s: None)
    with patch.object(requests.Session, "get") as mock_get:
        mock_get.return_value = MagicMock(status_code=500)
        with pytest.raises(requests.HTTPError):
            client.get("https://example.com/a")

    assert mock_get.call_count == 2


def test_uses_a_standard_anonymous_user_agent_by_default():
    client = RateLimitedClient()
    assert "Mozilla" in client.session.headers["User-Agent"]
    assert "law-cite" not in client.session.headers["User-Agent"].lower()
    assert "bot" not in client.session.headers["User-Agent"].lower()
