from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import httpx

_DEFAULT_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)
_RETRY_STATUS = frozenset({429, 500, 502, 503, 504})
_TRACKING_PREFIXES = ("utm_", "fbclid", "gclid")
_MAX_BACKOFF = 30.0


def canonical_url(url: str) -> str:
    """Normalize for cache/dedup keys: lower host, strip www + tracking params, sort query."""
    parts = urlsplit(url.strip())
    scheme = (parts.scheme or "https").lower()
    netloc = parts.netloc.lower()
    if netloc.startswith("www."):
        netloc = netloc[4:]
    query = sorted(
        (k, v)
        for k, v in parse_qsl(parts.query, keep_blank_values=True)
        if not k.lower().startswith(_TRACKING_PREFIXES)
    )
    path = parts.path.rstrip("/") or "/"
    return urlunsplit((scheme, netloc, path, urlencode(query), ""))


@dataclass(frozen=True)
class FetchResult:
    url: str
    final_url: str
    status: int
    text: str
    from_cache: bool = False

    @property
    def ok(self) -> bool:
        return 200 <= self.status < 300


class Fetcher:
    """Cached, rate-limited, retrying HTTP GET. Re-runs hit the on-disk cache.

    Caches successful (2xx) and permanent-not-found (404) responses keyed by the
    canonical URL; retries 5xx/429 and network errors with capped exponential
    backoff; never retries other 4xx.
    """

    def __init__(
        self,
        *,
        cache_dir: Path,
        delay: float = 0.5,
        timeout: float = 20.0,
        max_retries: int = 3,
        user_agent: str = _DEFAULT_UA,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self._cache_dir = cache_dir
        self._cache_dir.mkdir(parents=True, exist_ok=True)
        self._delay = delay
        self._max_retries = max_retries
        self._last_request = 0.0
        self.live_requests = 0
        self._client = httpx.Client(
            headers={"User-Agent": user_agent, "Accept-Language": "en;q=0.9"},
            follow_redirects=True,
            timeout=timeout,
            transport=transport,
        )

    def get(self, url: str, *, use_cache: bool = True) -> FetchResult:
        cache_path = self._cache_path(canonical_url(url))
        if use_cache:
            cached = self._read_cache(cache_path)
            if cached is not None:
                return cached
        result = self._get_live(url)
        if result.ok or result.status == 404:
            self._write_cache(cache_path, result)
        return result

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> Fetcher:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    def _get_live(self, url: str) -> FetchResult:
        delay = self._delay
        for attempt in range(self._max_retries + 1):
            self._throttle()
            try:
                response = self._client.get(url)
            except httpx.HTTPError:
                pass
            else:
                self.live_requests += 1
                if response.status_code not in _RETRY_STATUS or attempt == self._max_retries:
                    return FetchResult(url, str(response.url), response.status_code, response.text)
            if attempt < self._max_retries:
                time.sleep(delay)
                delay = min(delay * 2, _MAX_BACKOFF)
        return FetchResult(url, url, 0, "")

    def _throttle(self) -> None:
        wait = self._delay - (time.monotonic() - self._last_request)
        if wait > 0:
            time.sleep(wait)
        self._last_request = time.monotonic()

    def _cache_path(self, key: str) -> Path:
        digest = hashlib.sha1(key.encode("utf-8")).hexdigest()
        return self._cache_dir / f"{digest}.json"

    def _read_cache(self, path: Path) -> FetchResult | None:
        if not path.exists():
            return None
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None
        return FetchResult(
            url=data["url"],
            final_url=data["final_url"],
            status=data["status"],
            text=data["text"],
            from_cache=True,
        )

    def _write_cache(self, path: Path, result: FetchResult) -> None:
        payload = {
            "url": result.url,
            "final_url": result.final_url,
            "status": result.status,
            "text": result.text,
        }
        path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
