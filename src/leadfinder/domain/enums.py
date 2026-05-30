from __future__ import annotations

from enum import Enum


class LeadType(str, Enum):
    DISTRIBUTOR = "distributor"    # 经销/进口/批发 — target buyer
    RETAILER = "retailer"          # 零售/连锁 — buyer
    MANUFACTURER = "manufacturer"  # 品牌/制造商 — seller / competitor
    UNKNOWN = "unknown"


class Reachability(str, Enum):
    SAFE = "safe"
    RISKY = "risky"
    INVALID = "invalid"
    UNKNOWN = "unknown"


class Priority(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
