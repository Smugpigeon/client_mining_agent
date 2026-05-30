from __future__ import annotations

import re
from collections.abc import Callable

import dns.resolver

from leadfinder.domain.enums import Reachability
from leadfinder.domain.models import Verification
from leadfinder.infra import email_data

_SYNTAX = re.compile(r"^[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}$")


def _dns_mx(domain: str) -> bool:
    for record in ("MX", "A"):
        try:
            answers = dns.resolver.resolve(domain, record, lifetime=4.0)
        except Exception:
            continue
        if len(answers) > 0:
            return True
    return False


def _role_kind(local: str) -> str | None:
    head = re.split(r"[._-]", local, maxsplit=1)[0]
    if head in email_data.BUYER_ROLES:
        return "buyer"
    if head in email_data.SELLER_ROLES:
        return "seller"
    if head in email_data.GENERIC_ROLES:
        return "generic"
    return None


def _reachability(has_mx: bool, is_disposable: bool) -> Reachability:
    if is_disposable:
        return Reachability.RISKY
    if not has_mx:
        return Reachability.INVALID
    return Reachability.UNKNOWN  # no SMTP probe → the most we can assert is Unknown


class EmailChecker:
    """Verify an email without sending: syntax + MX + disposable/role/free tables → 4 buckets."""

    def __init__(self, *, mx_lookup: Callable[[str], bool] | None = None) -> None:
        self._mx_lookup = mx_lookup or _dns_mx

    def verify(self, email: str) -> Verification:
        address = email.strip().lower()
        if not _SYNTAX.match(address):
            return Verification(email=address, reachability=Reachability.INVALID)
        local, _, domain = address.partition("@")
        is_disposable = domain in email_data.DISPOSABLE_DOMAINS
        has_mx = self._mx_lookup(domain)
        role_kind = _role_kind(local)
        return Verification(
            email=address,
            reachability=_reachability(has_mx, is_disposable),
            has_mx=has_mx,
            is_disposable=is_disposable,
            is_role=role_kind is not None,
            is_free=domain in email_data.FREE_DOMAINS,
            role_kind=role_kind,
        )
