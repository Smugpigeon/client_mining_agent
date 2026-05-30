from __future__ import annotations

import base64
import hashlib
import hmac
import time
from collections.abc import Callable
from typing import Any

import httpx

HttpGet = Callable[[str, dict[str, str]], dict[str, Any]]
_JSCODE2SESSION = "https://api.weixin.qq.com/sns/jscode2session"


class WxAuthError(Exception):
    pass


def default_http_get(url: str, params: dict[str, str]) -> dict[str, Any]:
    data = httpx.get(url, params=params, timeout=10.0).json()
    return data if isinstance(data, dict) else {}


def code_to_openid(
    code: str, *, appid: str, secret: str, http_get: HttpGet = default_http_get
) -> str:
    """Exchange a Mini Program login code for the user's openid (jscode2session)."""
    data = http_get(
        _JSCODE2SESSION,
        {"appid": appid, "secret": secret, "js_code": code, "grant_type": "authorization_code"},
    )
    openid = data.get("openid")
    if not openid:
        raise WxAuthError(str(data.get("errmsg") or "jscode2session failed"))
    return str(openid)


def issue_token(openid: str, *, secret: str, ttl: int = 7 * 24 * 3600) -> str:
    """Stateless token: base64url(openid:exp) + '.' + hmac-sha256(body)."""
    payload = f"{openid}:{int(time.time()) + ttl}"
    body = base64.urlsafe_b64encode(payload.encode()).decode().rstrip("=")
    return f"{body}.{_sign(body, secret)}"


def verify_token(token: str, *, secret: str) -> str | None:
    """Return the openid if the token signature is valid and unexpired, else None."""
    body, _, signature = token.partition(".")
    if not signature or not hmac.compare_digest(signature, _sign(body, secret)):
        return None
    try:
        decoded = base64.urlsafe_b64decode(body + "=" * (-len(body) % 4)).decode()
        openid, _, exp = decoded.rpartition(":")
        if int(exp) < int(time.time()):
            return None
    except (ValueError, UnicodeDecodeError):
        return None
    return openid or None


def _sign(body: str, secret: str) -> str:
    return hmac.new(secret.encode(), body.encode(), hashlib.sha256).hexdigest()
