from __future__ import annotations

from leadfinder.config import keywords, scoring
from leadfinder.domain.enums import LeadType, Priority
from leadfinder.domain.models import Lead
from leadfinder.infra import email_data


class ScoreStage:
    """Stage: graduated buyer-focused score, then a High/Medium/Low priority bucket."""

    def process(self, lead: Lead) -> Lead | None:
        score = 0
        if lead.is_buyer:
            score += scoring.BUYER
        elif lead.lead_type is LeadType.MANUFACTURER:
            score -= scoring.SELLER_PENALTY
        if lead.skincare_relevant:
            score += scoring.SKINCARE
        if lead.email:
            score += scoring.HAS_EMAIL + scoring.EMAIL_STATUS.get(lead.email_status.value, 0)
            if lead.email.split("@", 1)[1] not in email_data.FREE_DOMAINS:
                score += scoring.CORPORATE_EMAIL
        country = (lead.country or "").lower()
        if country in keywords.TARGET_COUNTRIES:
            score += scoring.TARGET_COUNTRY
        elif country in keywords.SELLER_ORIGIN_COUNTRIES and not lead.is_buyer:
            score -= scoring.SELLER_ORIGIN_PENALTY
        if lead.website:
            score += scoring.HAS_WEBSITE
        if lead.phone:
            score += scoring.HAS_PHONE
        score = max(0, score)

        priority = (
            Priority.HIGH
            if score >= scoring.HIGH
            else Priority.MEDIUM
            if score >= scoring.MEDIUM
            else Priority.LOW
        )
        return lead.model_copy(update={"score": score, "priority": priority})
