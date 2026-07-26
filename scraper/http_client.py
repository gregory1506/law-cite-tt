import time

import requests

DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)


class RateLimitedClient:
    """HTTP client enforcing a minimum delay between requests and retrying
    transient/server errors with exponential backoff.

    Used exclusively against laws.gov.tt, a government site with no
    published crawl policy (robots.txt returns 404) — the delay, retry cap,
    and plain browser User-Agent here are self-imposed etiquette, not a
    performance optimization. See docs/superpowers/specs/
    2026-07-26-law-cite-tt-architecture-design.md, "Scraping etiquette".
    """

    def __init__(
        self,
        delay_seconds: float = 1.5,
        user_agent: str = DEFAULT_USER_AGENT,
        max_retries: int = 3,
        sleep_fn=time.sleep,
        time_fn=time.monotonic,
    ):
        self.delay_seconds = delay_seconds
        self.max_retries = max_retries
        self._sleep = sleep_fn
        self._time = time_fn
        self._last_request_at = None
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": user_agent})

    def get(self, url: str) -> requests.Response:
        last_exc = None
        for attempt in range(self.max_retries):
            self._wait_for_slot()
            try:
                response = self.session.get(url, timeout=30)
            except (requests.ConnectionError, requests.Timeout) as exc:
                last_exc = exc
                self._sleep(self.delay_seconds * (2**attempt))
                continue
            if response.status_code >= 500:
                last_exc = requests.HTTPError(
                    f"Server error {response.status_code} for {url}"
                )
                self._sleep(self.delay_seconds * (2**attempt))
                continue
            response.raise_for_status()
            return response
        raise last_exc

    def _wait_for_slot(self):
        now = self._time()
        if self._last_request_at is not None:
            elapsed = now - self._last_request_at
            if elapsed < self.delay_seconds:
                self._sleep(self.delay_seconds - elapsed)
        self._last_request_at = self._time()
