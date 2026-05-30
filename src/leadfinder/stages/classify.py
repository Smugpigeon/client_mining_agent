from __future__ import annotations

from leadfinder.config import keywords
from leadfinder.domain.enums import LeadType
from leadfinder.domain.models import Lead


class Classifier:
    """Stage: label buyer vs seller and skincare relevance from name/category/profile text.

    Email role-direction (purchasing@ vs sales@) is a separate signal applied later,
    after the email is found and verified.
    """

    def process(self, lead: Lead) -> Lead | None:
        blob = " ".join(
            part for part in (lead.company_name, lead.business, lead.profile) if part
        ).lower()
        skincare = any(word in blob for word in keywords.SKINCARE_KEYWORDS)
        buyer_hits = sum(word in blob for word in keywords.BUYER_KEYWORDS)
        seller_hits = sum(word in blob for word in keywords.SELLER_KEYWORDS)

        if buyer_hits > 0 and buyer_hits >= seller_hits:
            lead_type, is_buyer = LeadType.DISTRIBUTOR, True
        elif seller_hits > buyer_hits:
            lead_type, is_buyer = LeadType.MANUFACTURER, False
        else:
            # No keyword signal: a local firm at a West-Africa show is likely a buyer.
            lead_type = LeadType.UNKNOWN
            is_buyer = (lead.country or "").lower() in keywords.TARGET_COUNTRIES

        return lead.model_copy(
            update={"lead_type": lead_type, "is_buyer": is_buyer, "skincare_relevant": skincare}
        )
