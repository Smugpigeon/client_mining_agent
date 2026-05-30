from __future__ import annotations

from typing import Any

import pytest

from leadfinder.infra import wx_auth


def test_token_roundtrip() -> None:
    token = wx_auth.issue_token("user-123", secret="s3cret")
    assert wx_auth.verify_token(token, secret="s3cret") == "user-123"


def test_token_rejects_wrong_secret() -> None:
    token = wx_auth.issue_token("user-123", secret="s3cret")
    assert wx_auth.verify_token(token, secret="other") is None


def test_token_rejects_expired() -> None:
    token = wx_auth.issue_token("user-123", secret="s3cret", ttl=-1)
    assert wx_auth.verify_token(token, secret="s3cret") is None


def test_code_to_openid_with_fake_http() -> None:
    def fake_get(url: str, params: dict[str, str]) -> dict[str, Any]:
        return {"openid": "openid-abc", "session_key": "k"}

    assert wx_auth.code_to_openid("c", appid="a", secret="b", http_get=fake_get) == "openid-abc"


def test_code_to_openid_raises_on_error() -> None:
    def fake_get(url: str, params: dict[str, str]) -> dict[str, Any]:
        return {"errcode": 40029, "errmsg": "invalid code"}

    with pytest.raises(wx_auth.WxAuthError, match="invalid code"):
        wx_auth.code_to_openid("bad", appid="a", secret="b", http_get=fake_get)
