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


class Recipient(BaseModel):
    """One bulk-email recipient, with merge fields + context for AI personalization."""

    email: str
    company_name: str = ""
    country: str = ""
    business: str = ""  # 主营/品类,供 AI 个性化参考
    website: str = ""


class UserProfile(BaseModel):
    """The mini-program user's own identity — feeds the agent skill + email signature."""

    company: str = ""  # 我方公司/品牌
    products_desc: str = ""  # 主营/卖什么(一句话)
    markets: str = ""  # 目标市场
    signer: str = ""  # 邮件落款名
    language: str = "英文"  # AI 写信语言偏好


class ProductBlock(BaseModel):
    """One product's marketing block, included in outreach emails."""

    name: str
    intro: str = ""
    highlights: list[str] = []
    price: str = ""


class OutboundEmail(BaseModel):
    """A rendered, ready-to-send email (plain text + optional HTML)."""

    to: str
    subject: str
    body: str
    html: str = ""


class SendResult(BaseModel):
    """Outcome of one send (or a dry-run preview)."""

    to: str
    ok: bool
    error: str | None = None
    preview: str | None = None


class ChatMessage(BaseModel):
    """One turn in the LLM chat dialog (role: user | assistant)."""

    role: str
    content: str
