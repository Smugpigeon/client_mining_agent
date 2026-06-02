from __future__ import annotations

from leadfinder.domain.models import OutboundEmail, ProductBlock, Recipient, SendResult
from leadfinder.outreach import build_email, render, run_campaign


class _FakeSender:
    def __init__(self) -> None:
        self.sent: list[OutboundEmail] = []

    def send(self, email: OutboundEmail) -> SendResult:
        self.sent.append(email)
        return SendResult(to=email.to, ok=True)


def test_render_merges_fields() -> None:
    r = Recipient(email="a@b.com", company_name="Acme", country="Nigeria")
    assert render("你好 {{company_name}}（{{country}}）", r) == "你好 Acme（Nigeria）"
    # 友好中文写法也要替换
    assert render("你好「公司名」（「国家」）", r) == "你好Acme（Nigeria）"


def test_build_email_appends_unsubscribe_footer() -> None:
    email = build_email("Hi", "正文", Recipient(email="a@b.com"), "Tom")
    assert "退订" in email.body
    assert email.body.startswith("正文")


def test_dry_run_previews_without_sending() -> None:
    sender = _FakeSender()
    results = list(
        run_campaign(
            sender=sender,
            recipients=[Recipient(email="a@b.com", company_name="Acme")],
            subject="Hi {{company_name}}",
            body="正文",
            dry_run=True,
            delay=0,
        )
    )
    assert sender.sent == []
    assert results[0].ok and results[0].preview is not None and "Acme" in results[0].preview


def test_send_dedups_and_skips_invalid() -> None:
    sender = _FakeSender()
    recipients = [
        Recipient(email="a@b.com", company_name="A"),
        Recipient(email="A@b.com"),  # duplicate (case-insensitive)
        Recipient(email="not-an-email"),
    ]
    results = list(
        run_campaign(
            sender=sender, recipients=recipients, subject="s", body="b", dry_run=False, delay=0
        )
    )
    assert len(sender.sent) == 1
    assert [r.ok for r in results] == [True, False, False]


def test_products_render_in_text_and_html() -> None:
    p = ProductBlock(
        name="玻尿酸面膜", intro="深层补水", highlights=["医用级", "敏感肌可用"], price="US$0.9/片"
    )
    email = build_email("Hi", "正文", Recipient(email="a@b.com"), "Tom", [p])
    # plain-text part carries the product, after the message body
    assert "玻尿酸面膜" in email.body and "医用级" in email.body
    # html part is a styled card with name + price
    assert "玻尿酸面膜" in email.html and "<table" in email.html and "US$0.9" in email.html


def test_personalizer_overrides_template() -> None:
    sender = _FakeSender()
    results = list(
        run_campaign(
            sender=sender,
            recipients=[Recipient(email="a@b.com", company_name="Acme")],
            subject="模板主题",
            body="模板正文",
            personalizer=lambda r: (f"专属 {r.company_name}", "AI 写的正文"),
            dry_run=True,
            delay=0,
        )
    )
    assert results[0].preview is not None
    assert "专属 Acme" in results[0].preview
    assert "AI 写的正文" in results[0].preview
    assert "模板正文" not in results[0].preview
