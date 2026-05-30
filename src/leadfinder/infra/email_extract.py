from __future__ import annotations

import re

from bs4 import BeautifulSoup

_EMAIL_RE = re.compile(r"[a-z0-9._+-]+@[a-z0-9.-]+\.[a-z]{2,}", re.IGNORECASE)
_JUNK_TLDS = frozenset({
    "png", "jpg", "jpeg", "gif", "svg", "webp", "css", "js", "json",
    "pdf", "mp4", "ico", "woff", "woff2",
})
_JUNK_DOMAINS = frozenset({
    "example.com", "domain.com", "email.com", "sentry.io", "wixpress.com",
    "wix.com", "godaddy.com", "schema.org", "w3.org",
})
_JUNK_LOCAL = ("noreply", "no-reply", "donotreply")
_SKIP_HOSTS = (
    "facebook.", "instagram.", "twitter.", "linkedin.", "youtube.", "wa.me",
    "whatsapp.", "t.me", "alibaba.", "made-in-china.", "tiktok.",
)


def website_is_enrichable(url: str) -> bool:
    """Skip social profiles and marketplace storefronts — they never hold the buyer's own email."""
    low = url.lower()
    return low.startswith(("http://", "https://")) and not any(h in low for h in _SKIP_HOSTS)


def decode_cfemail(token: str) -> str:
    """Decode a Cloudflare data-cfemail token (XOR with the first byte)."""
    try:
        key = int(token[:2], 16)
        return "".join(chr(int(token[i : i + 2], 16) ^ key) for i in range(2, len(token), 2))
    except ValueError:
        return ""


def extract_emails(html: str) -> set[str]:
    emails: set[str] = set()
    for token in re.findall(r'data-cfemail="([0-9a-fA-F]+)"', html):
        decoded = decode_cfemail(token)
        if decoded:
            emails.add(decoded)
    soup = BeautifulSoup(html, "lxml")
    for anchor in soup.find_all("a", href=True):
        href = str(anchor["href"]).strip()
        if href.lower().startswith("mailto:"):
            emails.add(href[7:].split("?")[0].strip())
    emails.update(_EMAIL_RE.findall(html))
    return emails


def extract_phones(html: str) -> list[str]:
    soup = BeautifulSoup(html, "lxml")
    phones: list[str] = []
    for anchor in soup.find_all("a", href=True):
        href = str(anchor["href"]).strip()
        if href.lower().startswith("tel:"):
            phone = href[4:].strip()
            if phone and phone not in phones:
                phones.append(phone)
    return phones


def filter_emails(emails: set[str], site_domain: str) -> list[str]:
    """Drop junk, dedupe, rank corporate-domain matches first."""
    cleaned: list[str] = []
    for raw in emails:
        email = raw.strip().strip(".").lower()
        if "@" not in email or "%" in email or "//" in email:
            continue
        local, _, domain = email.partition("@")
        if not local or "." not in domain:
            continue
        if domain.rsplit(".", 1)[-1] in _JUNK_TLDS:
            continue
        if any(domain == junk or domain.endswith("." + junk) for junk in _JUNK_DOMAINS):
            continue
        if any(bad in local for bad in _JUNK_LOCAL):
            continue
        cleaned.append(email)
    site = site_domain.lower().removeprefix("www.")

    def rank(email: str) -> int:
        domain = email.split("@", 1)[1]
        if site and (domain == site or domain.endswith("." + site)):
            return 0
        return 1

    return sorted(dict.fromkeys(cleaned), key=rank)
