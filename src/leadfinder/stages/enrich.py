from __future__ import annotations

import re
from typing import Any
from urllib.parse import urljoin, urlsplit

from bs4 import BeautifulSoup

from leadfinder.domain.models import Lead
from leadfinder.infra import email_extract
from leadfinder.infra.http import Fetcher

_CONTACT_HINT = re.compile(r"contact|about|reach|connect", re.IGNORECASE)


def _with_scheme(url: str) -> str:
    url = url.strip()
    return url if url.startswith(("http://", "https://")) else "https://" + url


class EnrichStage:
    """Stage: fetch the lead's website, extract the best email (+ phone). Skips if already set."""

    def __init__(self, *, fetcher: Fetcher, max_contact_pages: int = 2) -> None:
        self._fetcher = fetcher
        self._max_contact_pages = max_contact_pages

    def process(self, lead: Lead) -> Lead | None:
        if lead.email or not lead.website or not email_extract.website_is_enrichable(lead.website):
            return lead
        home_url = _with_scheme(lead.website)
        home = self._fetcher.get(home_url)
        if not home.ok:
            return lead
        site_domain = urlsplit(home_url).netloc.lower().removeprefix("www.")
        emails = email_extract.extract_emails(home.text)
        phones = email_extract.extract_phones(home.text)
        for link in self._contact_links(home.text, home_url):
            page = self._fetcher.get(link)
            if page.ok:
                emails |= email_extract.extract_emails(page.text)
                phones += email_extract.extract_phones(page.text)

        update: dict[str, Any] = {}
        best = email_extract.filter_emails(emails, site_domain)
        if best:
            update["email"] = best[0]
        if phones and not lead.phone:
            update["phone"] = phones[0]
        return lead.model_copy(update=update) if update else lead

    def _contact_links(self, html: str, base: str) -> list[str]:
        soup = BeautifulSoup(html, "lxml")
        links: list[str] = []
        for anchor in soup.find_all("a", href=True):
            if _CONTACT_HINT.search(str(anchor["href"])):
                full = urljoin(base, str(anchor["href"]))
                if full not in links:
                    links.append(full)
            if len(links) >= self._max_contact_pages:
                break
        return links
