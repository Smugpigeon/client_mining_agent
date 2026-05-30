from __future__ import annotations

SKINCARE_KEYWORDS = (
    "skincare", "skin care", "cosmetic", "cosmetics", "beauty", "personal care",
    "perfume", "fragrance", "hair", "makeup", "make-up", "lotion", "cream", "soap",
    "toiletries", "grooming", "spa", "wellness", "护肤", "美妆", "化妆",
)
BUYER_KEYWORDS = (
    "distributor", "distribution", "importer", "import", "wholesale", "wholesaler",
    "trading", "traders", "retail", "retailer", "stores", "supermarket", "pharmacy",
    "chain", "sourcing", "procurement", "reseller", "dealer", "supplies", "supply",
)
SELLER_KEYWORDS = (
    "manufacturer", "manufacturing", "factory", "industries", "industry", "producer",
    "production", "laboratoire", "laboratories", "oem", "odm", "exporter",
    "our brand", "we produce", "we manufacture",
)
TARGET_COUNTRIES = frozenset({
    "nigeria", "ghana", "kenya", "south africa", "egypt", "morocco", "tanzania",
    "uganda", "ethiopia", "cote d'ivoire", "ivory coast", "senegal", "cameroon",
    "angola", "benin", "togo", "zambia", "rwanda", "united arab emirates", "uae",
    "saudi arabia", "qatar",
})
SELLER_ORIGIN_COUNTRIES = frozenset({
    "china", "india", "pakistan", "turkiye", "turkey", "france", "italy",
    "united states of america", "usa", "south korea", "korea", "thailand",
})
