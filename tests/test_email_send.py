from __future__ import annotations

from leadfinder.domain.models import OutboundEmail
from leadfinder.domain.protocols import EmailSender
from leadfinder.infra.email_send import SmtpConfig, SmtpSender


def test_smtp_sender_is_an_email_sender() -> None:
    assert isinstance(SmtpSender(config=SmtpConfig(), send_fn=lambda _c, _e: None), EmailSender)


def test_smtp_sender_ok() -> None:
    sent: list[OutboundEmail] = []
    sender = SmtpSender(config=SmtpConfig(host="h"), send_fn=lambda _c, email: sent.append(email))
    result = sender.send(OutboundEmail(to="a@b.com", subject="s", body="b"))

    assert result.ok is True
    assert len(sent) == 1


def test_smtp_sender_reports_failure_without_raising() -> None:
    def boom(_c: SmtpConfig, _e: OutboundEmail) -> None:
        raise RuntimeError("smtp down")

    sender = SmtpSender(config=SmtpConfig(), send_fn=boom)
    result = sender.send(OutboundEmail(to="a@b.com", subject="s", body="b"))

    assert result.ok is False
    assert result.error is not None and "smtp down" in result.error


def test_configured_property() -> None:
    assert not SmtpConfig().configured
    assert SmtpConfig(host="h", user="u", password="p", from_email="f@x.com").configured
