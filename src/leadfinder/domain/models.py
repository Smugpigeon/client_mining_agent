from __future__ import annotations

from pydantic import BaseModel, Field

from leadfinder.domain.enums import LeadType, Priority, Reachability

SCHEMA_VERSION = 1
# v1: initial Lead / RawRecord / Verification schema.


class SearchParams(BaseModel):
    """What a source is asked to find."""

    product_keywords: tuple[str, ...] = ()
    target_countries: tuple[str, ...] = ()
    limit: int | None = None


class RawRecord(BaseModel):
    """Discovery output from a source, before enrichment and validation."""

    source: str
    source_url: str | None = None
    company_name: str
    country: str | None = None
    website: str | None = None
    category: str | None = None
    profile: str | None = None
    extra: dict[str, str] = Field(default_factory=dict)


class Verification(BaseModel):
    """Result of verifying one email (AfterShip/Reacher-style signals, no SMTP by default)."""

    email: str
    reachability: Reachability = Reachability.UNKNOWN
    has_mx: bool = False
    is_disposable: bool = False
    is_role: bool = False
    is_free: bool = False
    role_kind: str | None = None  # "buyer" | "seller" | "generic" | None


class Lead(BaseModel):
    """The record that flows through the processing pipeline and gets exported."""

    company_name: str
    country: str | None = None
    website: str | None = None
    business: str | None = None  # 主营 / 品类
    profile: str | None = None
    email: str | None = None
    email_status: Reachability = Reachability.UNKNOWN
    phone: str | None = None
    lead_type: LeadType = LeadType.UNKNOWN
    is_buyer: bool = False
    skincare_relevant: bool = False
    size_estimate: str | None = None
    source: str
    source_url: str | None = None
    score: int = 0
    priority: Priority = Priority.LOW
    schema_version: int = SCHEMA_VERSION
