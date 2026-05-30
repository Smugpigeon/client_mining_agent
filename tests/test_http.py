from __future__ import annotations

from pathlib import Path

import httpx

from leadfinder.infra.http import Fetcher, canonical_url


def test_canonical_url_normalizes() -> None:
    assert (
        canonical_url("https://WWW.Example.com/path/?b=2&a=1&utm_source=x")
        == "https://example.com/path?a=1&b=2"
    )
    assert canonical_url("http://example.com") == "http://example.com/"


def test_cache_hit_skips_network(tmp_path: Path) -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(200, text="hello")

    with Fetcher(cache_dir=tmp_path, delay=0.0, transport=httpx.MockTransport(handler)) as fetcher:
        first = fetcher.get("https://example.com/")
        second = fetcher.get("https://example.com/?utm_source=ad")  # same canonical URL

    assert first.text == "hello"
    assert first.from_cache is False
    assert second.from_cache is True
    assert calls == 1


def test_retries_5xx_then_succeeds(tmp_path: Path) -> None:
    attempts = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        return httpx.Response(503) if attempts == 1 else httpx.Response(200, text="ok")

    with Fetcher(
        cache_dir=tmp_path, delay=0.0, max_retries=2, transport=httpx.MockTransport(handler)
    ) as fetcher:
        result = fetcher.get("https://example.com/")

    assert result.ok is True
    assert attempts == 2


def test_no_retry_on_404(tmp_path: Path) -> None:
    attempts = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        return httpx.Response(404)

    with Fetcher(
        cache_dir=tmp_path, delay=0.0, max_retries=2, transport=httpx.MockTransport(handler)
    ) as fetcher:
        result = fetcher.get("https://example.com/missing")

    assert result.status == 404
    assert attempts == 1
