from __future__ import annotations

BASE = "https://www.beautywestafrica.com"
LIST_HANDLER = BASE + "/ExhibitorListHandler2025.ashx"
DETAIL_URL = BASE + "/ExhibitorDetails2025.aspx?ExhiId={exhibitor_id}"
LIST_QUERY_ALL = "~~~"  # alphabet~search~product~country; all empty = every exhibitor
PAGE_SIZE = 16  # server caps page size at 16
SOURCE_NAME = "Beauty West Africa 2025"

# Detail-page parsing: name + profile live in stable ASP.NET label ids; website /
# country / category are the value after a bold label inside the profile card.
NAME_ID = "cphContents_lblCompanyNamehead"
PROFILE_ID = "cphContents_lblOnlineProfile"
LABEL_WEBSITE = "Website:"
LABEL_COUNTRY = "Country:"
LABEL_CATEGORY = "Product Category:"
