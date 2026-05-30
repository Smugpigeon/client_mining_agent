from __future__ import annotations

# Graduated, buyer-focused weights (waterfall-gtm style). Tune here, not in code.
BUYER = 25
SELLER_PENALTY = 25
SKINCARE = 12
HAS_EMAIL = 20
EMAIL_STATUS = {"safe": 12, "unknown": 8, "risky": -5, "invalid": -15}
CORPORATE_EMAIL = 5
TARGET_COUNTRY = 12
SELLER_ORIGIN_PENALTY = 5
HAS_WEBSITE = 4
HAS_PHONE = 3

# Priority cut-offs on the resulting score.
HIGH = 60
MEDIUM = 35
