from __future__ import annotations

from collections.abc import Iterable, Sequence
from pathlib import Path
from typing import Protocol, runtime_checkable

from leadfinder.domain.models import (
    Lead,
    OutboundEmail,
    RawRecord,
    SearchParams,
    SendResult,
    Verification,
)


@runtime_checkable
class LeadSource(Protocol):
    """A pluggable discovery channel (trade-show directory, customs data, ...)."""

    name: str

    def fetch(self, params: SearchParams) -> Iterable[RawRecord]: ...


@runtime_checkable
class Stage(Protocol):
    """One processing step. Return None to DROP the lead (caller logs the reason)."""

    def process(self, lead: Lead) -> Lead | None: ...


@runtime_checkable
class EmailVerifier(Protocol):
    """Verify a single email without sending (data-table + MX; SMTP behind a flag)."""

    def verify(self, email: str) -> Verification: ...


@runtime_checkable
class Writer(Protocol):
    """Persist the ranked leads to a file; returns the written path."""

    def write(self, leads: Sequence[Lead]) -> Path: ...


@runtime_checkable
class EmailSender(Protocol):
    """Send one email. Never raises on a single failure — returns a SendResult."""

    def send(self, email: OutboundEmail) -> SendResult: ...
