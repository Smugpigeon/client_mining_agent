from __future__ import annotations

import re
import time
from collections.abc import Iterator, Sequence
from html import escape

from leadfinder.domain.models import OutboundEmail, ProductBlock, Recipient, SendResult
from leadfinder.domain.protocols import EmailSender

_PLACEHOLDER = re.compile(r"\{\{\s*(\w+)\s*\}\}")


def render(template: str, recipient: Recipient) -> str:
    """Replace {{company_name}} / {{country}} / {{email}} merge fields."""
    values = {
        "company_name": recipient.company_name or "贵公司",
        "country": recipient.country or "",
        "email": recipient.email,
    }
    return _PLACEHOLDER.sub(lambda m: values.get(m.group(1), m.group(0)), template)


def _products_text(products: Sequence[ProductBlock]) -> str:
    blocks = []
    for p in products:
        lines = [f"【{p.name}】" + (f"  {p.price}" if p.price else "")]
        if p.intro:
            lines.append(p.intro)
        lines += [f"· {h}" for h in p.highlights]
        blocks.append("\n".join(lines))
    return "\n\n".join(blocks)


def _products_html(products: Sequence[ProductBlock]) -> str:
    cards = []
    for p in products:
        price = (
            f'<div style="color:#b8860b;font-size:13px;margin-top:2px;">{escape(p.price)}</div>'
            if p.price
            else ""
        )
        intro = (
            f'<div style="margin-top:8px;color:#444;">{escape(p.intro)}</div>' if p.intro else ""
        )
        highlights = ""
        if p.highlights:
            items = "".join(f"<li>{escape(h)}</li>" for h in p.highlights)
            highlights = f'<ul style="margin:8px 0 0;padding-left:18px;color:#555;">{items}</ul>'
        cards.append(
            '<table width="100%" cellpadding="0" cellspacing="0" style="border:1px solid #e6e6e6;'
            'border-radius:10px;margin:14px 0;background:#fafafa;"><tr>'
            '<td style="padding:16px 20px;">'
            f'<div style="font-size:17px;font-weight:700;color:#1b3a5f;">{escape(p.name)}</div>'
            f"{price}{intro}{highlights}</td></tr></table>"
        )
    return "".join(cards)


def _footer_text(from_name: str) -> str:
    return f"\n\n— {from_name or '我们'}\n如不希望再收到此类邮件，请直接回复「退订」。"


def build_email(
    subject: str,
    body: str,
    recipient: Recipient,
    from_name: str,
    products: Sequence[ProductBlock] = (),
) -> OutboundEmail:
    message = render(body, recipient)
    text = (
        message + ("\n\n" + _products_text(products) if products else "") + _footer_text(from_name)
    )
    html = (
        '<div style="font-family:-apple-system,Segoe UI,Roboto,sans-serif;max-width:600px;'
        'margin:0 auto;color:#333;line-height:1.6;font-size:15px;">'
        f'<div style="white-space:pre-wrap;">{escape(message)}</div>'
        f"{_products_html(products)}"
        f'<div style="margin-top:22px;color:#999;font-size:12px;">— {escape(from_name or "我们")}'
        "<br>如不希望再收到此类邮件，请直接回复「退订」。</div></div>"
    )
    return OutboundEmail(
        to=recipient.email, subject=render(subject, recipient), body=text, html=html
    )


def run_campaign(
    *,
    sender: EmailSender,
    recipients: Sequence[Recipient],
    subject: str,
    body: str,
    from_name: str = "",
    products: Sequence[ProductBlock] = (),
    dry_run: bool = True,
    delay: float = 0.8,
) -> Iterator[SendResult]:
    """Render and (unless dry_run) send to each recipient. Dedups, skips invalid, rate-limits."""
    seen: set[str] = set()
    for recipient in recipients:
        addr = recipient.email.strip().lower()
        if not addr or "@" not in addr or addr in seen:
            yield SendResult(to=recipient.email, ok=False, error="无效或重复邮箱，已跳过")
            continue
        seen.add(addr)
        email = build_email(subject, body, recipient, from_name, products)
        if dry_run:
            yield SendResult(to=email.to, ok=True, preview=f"主题：{email.subject}\n\n{email.body}")
            continue
        yield sender.send(email)
        if delay > 0:
            time.sleep(delay)
