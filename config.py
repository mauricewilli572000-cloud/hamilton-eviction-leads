"""Hamilton County (Cincinnati), OH eviction leads - tired landlords.

Source: Hamilton County Clerk of Courts (courtclerk.org), Municipal Civil eviction hearings
  - Eviction schedule by date: /data/eviction_schedule.php?chosendate=M/D/YYYY&court=MCV&location=EVIM
  - Case party info:            POST /data/case_summary.php  casenumber=..., sec=party
    The defendant's address is the rental being evicted; the plaintiff's is the landlord's.
"""
from pathlib import Path

BASE = "https://www.courtclerk.org"
SCHEDULE_URL = BASE + "/data/eviction_schedule.php"
SUMMARY_URL = BASE + "/data/case_summary.php"
REFERER = BASE + "/records-search/eviction-schedule-search/"
DAYS_BACK = 45            # schedules re-read each run (cases are cached, only new ones are looked up)
DAYS_FORWARD = 21
MAX_CASE_LOOKUPS = 1500   # per run; the rest are picked up the next day
REQUEST_DELAY = 1.0       # seconds between requests - be polite to the clerk's site

EXCLUDE_PLAINTIFFS = ["CINCINNATI METROPOLITAN HOUSING", "CMHA", "HOUSING AUTHORITY", "CITY OF CINCINNATI",
                      "HAMILTON COUNTY LAND", "LAND REUTILIZATION", "PORT AUTHORITY"]
ENTITY_WORDS = ["LLC", "L.L.C", "INC", "CORP", "COMPANY", " CO ", "LTD", " LP", "LLP", "TRUST", "PROPERTIES",
                "HOLDINGS", "INVESTMENTS", "MANAGEMENT", "REALTY", "HOMES", "APARTMENTS", "ASSOCIATES", "GROUP",
                "PARTNERS", "ENTERPRISES", "VENTURES", "CAPITAL", "RENTALS", "HOUSING", "CHURCH", "BANK", "FUND",
                "LEASECO", "PORTFOLIO", "VILLAGE", "COMMONS", "TOWNHOMES"]
LARGE_MANAGER_WORDS = ["MANAGEMENT", "APARTMENTS", "COMMUNITIES", "RESIDENTIAL", "LEASECO", "TOWNHOMES", "COMMONS"]

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
DOCS_DIR = ROOT / "docs"
CASES_JSON = DATA_DIR / "cases.json"
DASHBOARD_JSON = DOCS_DIR / "hamilton_evictions.json"
GHL_CSV = DATA_DIR / "ghl_hamilton_evictions.csv"
DOCS_CSV = DOCS_DIR / "ghl_hamilton_evictions.csv"
