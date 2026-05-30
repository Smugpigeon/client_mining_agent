from __future__ import annotations

# Role-account local-parts, keyed by buyer/seller direction (AfterShip-style, trimmed).
BUYER_ROLES = frozenset({
    "purchasing", "purchase", "buyer", "buying", "procurement", "sourcing",
    "import", "imports", "importer",
})
SELLER_ROLES = frozenset({"sales", "export", "exports", "marketing"})
GENERIC_ROLES = frozenset({
    "info", "contact", "admin", "office", "hello", "enquiry", "enquiries",
    "support", "help", "mail", "general", "team",
})

# Common free-mail providers (a B2B buyer on a corporate domain scores higher).
FREE_DOMAINS = frozenset({
    "gmail.com", "yahoo.com", "yahoo.co.uk", "hotmail.com", "outlook.com",
    "live.com", "aol.com", "icloud.com", "qq.com", "163.com", "126.com",
    "sina.com", "gmx.com", "mail.com", "protonmail.com", "yandex.com",
})

# Disposable domains — a trimmed seed; the full ~123k upstream list can be vendored later.
DISPOSABLE_DOMAINS = frozenset({
    "mailinator.com", "guerrillamail.com", "10minutemail.com", "tempmail.com",
    "trashmail.com", "yopmail.com", "getnada.com", "temp-mail.org",
    "throwawaymail.com", "dispostable.com",
})
