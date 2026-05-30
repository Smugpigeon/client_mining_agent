from __future__ import annotations

from typing import Any

from leadfinder.domain.models import Lead, Verification
from leadfinder.domain.protocols import EmailVerifier
from leadfinder.infra.email_verify import EmailChecker


class VerifyStage:
    """Stage: verify lead.email -> reachability bucket; nudge buyer on a buyer-role address."""

    def __init__(self, *, verifier: EmailVerifier | None = None) -> None:
        self._verifier = verifier or EmailChecker()

    def process(self, lead: Lead) -> Lead | None:
        if not lead.email:
            return lead
        result: Verification = self._verifier.verify(lead.email)
        update: dict[str, Any] = {"email_status": result.reachability}
        if result.role_kind == "buyer":
            update["is_buyer"] = True
        return lead.model_copy(update=update)
