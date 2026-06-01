from __future__ import annotations

import os
import smtplib
import ssl
from collections.abc import Callable
from dataclasses import dataclass
from email.message import EmailMessage

from leadfinder.domain.models import OutboundEmail, SendResult

SendFn = Callable[["SmtpConfig", OutboundEmail], None]


@dataclass
class SmtpConfig:
    host: str = ""
    port: int = 587
    user: str = ""
    password: str = ""
    from_email: str = ""
    from_name: str = ""

    @property
    def configured(self) -> bool:
        return bool(self.host and self.user and self.password and self.from_email)


def smtp_config_from_env() -> SmtpConfig:
    return SmtpConfig(
        host=os.environ.get("SMTP_HOST", ""),
        port=int(os.environ.get("SMTP_PORT", "587")),
        user=os.environ.get("SMTP_USER", ""),
        password=os.environ.get("SMTP_PASSWORD", ""),
        from_email=os.environ.get("SMTP_FROM", "") or os.environ.get("SMTP_USER", ""),
        from_name=os.environ.get("SMTP_FROM_NAME", ""),
    )


def _send_via_smtp(config: SmtpConfig, email: OutboundEmail) -> None:
    message = EmailMessage()
    message["From"] = (
        f"{config.from_name} <{config.from_email}>" if config.from_name else config.from_email
    )
    message["To"] = email.to
    message["Subject"] = email.subject
    message.set_content(email.body)
    if email.html:
        message.add_alternative(email.html, subtype="html")
    context = ssl.create_default_context()
    with smtplib.SMTP(config.host, config.port, timeout=20) as server:
        server.starttls(context=context)
        server.login(config.user, config.password)
        server.send_message(message)


class SmtpSender:
    """EmailSender via SMTP (STARTTLS). Inject `send_fn` in tests to avoid real sending."""

    def __init__(self, *, config: SmtpConfig, send_fn: SendFn | None = None) -> None:
        self._config = config
        self._send_fn = send_fn or _send_via_smtp

    def send(self, email: OutboundEmail) -> SendResult:
        try:
            self._send_fn(self._config, email)
            return SendResult(to=email.to, ok=True)
        except Exception as exc:  # one bad send must never abort the whole campaign
            return SendResult(to=email.to, ok=False, error=str(exc))
