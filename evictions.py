"""Hamilton County eviction schedules + case party info -> landlord leads."""
from __future__ import annotations

import datetime as dt
import hashlib
import html
import logging
import re
import time

import config

log = logging.getLogger(__name__)

try:
    from curl_cffi import requests as _http
    S = _http.Session(impersonate="chrome")
except Exception:  # pragma: no cover
    import requests as _http
    S = _http.Session()
HEADERS = {"Referer": config.REFERER}


def _req(method, url, **kw):
    last = None
    for attempt in range(4):
        try:
            r = S.request(method, url, timeout=90, headers=HEADERS, **kw)
            if r.status_code == 200:
                return r
            last = f"HTTP {r.status_code}"
        except Exception as e:  # noqa: BLE001
            last = str(e)
        time.sleep(5 * (attempt + 1))
    raise RuntimeError(f"{method} {url} failed: {last}")


def _cell(s: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", s)).replace("\xa0", " ")).strip()


def _rows(page: str) -> list[list[str]]:
    return [[_cell(c) for c in re.findall(r"<t[hd][^>]*>(.*?)</t[hd]>", r, re.S)]
            for r in re.findall(r"<tr[^>]*>(.*?)</tr>", page, re.S)]


# ----------------------------------------------------------------- schedule
def parse_schedule(page: str, day: str) -> list[dict]:
    out, cur = [], None
    for cells in _rows(page):
        if not cells:
            continue
        head = cells[0].rstrip(":").lower()
        if head == "case #" and len(cells) > 1:
            cur = {"case_number": cells[1], "hearing_date": day, "plaintiff": "", "defendant": ""}
            out.append(cur)
        elif cur and head == "plaintiff" and len(cells) > 1:
            cur["plaintiff"] = cells[1]
            cur["plaintiff_attorney"] = cells[3] if len(cells) > 3 else ""
        elif cur and head == "defendant" and len(cells) > 1:
            cur["defendant"] = cells[1]
        elif cur and head == "next action" and len(cells) > 1:
            cur["next_action"] = cells[1]
    return [c for c in out if re.match(r"\d{2}CV\d+", c["case_number"])]


def fetch_schedule(day: dt.date) -> list[dict]:
    d = f"{day.month}/{day.day}/{day.year}"
    r = _req("GET", config.SCHEDULE_URL, params={"chosendate": d, "court": "MCV", "location": "EVIM"})
    return parse_schedule(r.text, day.isoformat())


# ----------------------------------------------------------------- case details
def parse_party(page: str) -> dict:
    """Filed date, case type, and plaintiff/defendant names + addresses from the party page."""
    text = _cell(page)
    info = {}
    m = re.search(r"Filed Date:\s*(\d{1,2}/\d{1,2}/\d{4})", text)
    if m:
        mo, d, y = m.group(1).split("/")
        info["filed_date"] = f"{y}-{int(mo):02d}-{int(d):02d}"
    m = re.search(r"Case Type:\s*(\S+)", text)
    info["case_type"] = m.group(1) if m else ""
    parties = []
    for cells in _rows(page):
        if len(cells) >= 3 and re.match(r"^[PD]\s*\d+$", cells[2]):
            parties.append({"name": cells[0], "address": cells[1], "role": cells[2][0]})
    info["plaintiffs"] = [p for p in parties if p["role"] == "P"]
    info["defendants"] = [p for p in parties if p["role"] == "D"]
    return info


def fetch_case(case_number: str) -> dict:
    r = _req("POST", config.SUMMARY_URL, data={"casenumber": case_number, "validate_case_number": "1", "sec": "party"})
    return parse_party(r.text)


TAIL_RE = re.compile(r"^(.*?)\s+([A-Z]{2})\s+(\d{5})(?:-?\d{4})?$")
STREET_RE = re.compile(r"^(.*?\b(?:ST|STREET|AVE|AVENUE|AV|RD|ROAD|DR|DRIVE|CT|COURT|LN|LANE|PL|PLACE|BLVD|WAY|PIKE|"
                       r"TER|TERRACE|CIR|CIRCLE|PKWY|HWY|TRL|TRAIL|RUN|ROW|SQ|ALY|LOOP)\b\.?"
                       r"(?:\s+(?:APT|UNIT|#|STE|LOT)\s*\S+|\s+#\S+)?)\s+(.+)$")


def split_addr(a: str) -> dict:
    """'7053 NOBLE COURT CINCINNATI OH 45239' -> street / city / state / zip (best effort)."""
    a = re.sub(r"\s+", " ", a or "").strip().upper()
    m = TAIL_RE.match(a)
    if not m:
        return {"street": a, "city": "", "state": "", "zip": ""}
    pre, state, zipc = m.groups()
    sm = STREET_RE.match(pre)
    if sm:
        street, city = sm.group(1), sm.group(2)
    else:                       # no suffix found: assume the last word is the city
        street, _, city = pre.rpartition(" ")
    return {"street": street.strip(), "city": city.strip().title(), "state": state, "zip": zipc}


# ----------------------------------------------------------------- leads
def landlord_key(name: str) -> str:
    n = re.sub(r"[^A-Z0-9 ]", " ", name.upper())
    n = re.sub(r"\b(LLC|L L C|INC|CORP|CORPORATION|CO|COMPANY|LTD|LP|LLP|THE|DBA)\b", " ", n)
    return re.sub(r"\s+", " ", n).strip()


def is_entity(name: str) -> bool:
    n = f" {name.upper()} "
    return any(w in n for w in config.ENTITY_WORDS)


def excluded(name: str) -> bool:
    return any(w in name.upper() for w in config.EXCLUDE_PLAINTIFFS)


def build_leads(cases: dict[str, dict], today: dt.date) -> list[dict]:
    groups: dict[str, list[dict]] = {}
    for c in cases.values():
        if not c.get("detail") or excluded(c["plaintiff"]):
            continue
        k = landlord_key(c["plaintiff"])
        if k:
            groups.setdefault(k, []).append(c)
    y_ago = (today - dt.timedelta(days=365)).isoformat()
    q_ago = (today - dt.timedelta(days=90)).isoformat()
    leads = []
    for k, cs in groups.items():
        name = cs[0]["plaintiff"]
        props, mail = {}, {}
        for c in cs:
            for d in c["detail"].get("defendants", []):
                a = split_addr(d["address"])
                if a["street"] and re.match(r"^\d", a["street"]):
                    props.setdefault(a["street"], f"{a['street']}, {a['city'] or 'Cincinnati'}, OH {a['zip']}".strip())
            for p in c["detail"].get("plaintiffs", []):
                if not mail and landlord_key(p["name"]) == k and p["address"]:
                    mail = split_addr(p["address"])
        dates = sorted(c["detail"].get("filed_date") or c["hearing_date"] for c in cs)
        n12 = sum(1 for d in dates if d >= y_ago)
        n90 = sum(1 for d in dates if d >= q_ago)
        entity = is_entity(name)
        out_state = bool(mail.get("state")) and mail["state"] != "OH"
        institutional = any(w in f" {name.upper()}" for w in config.INSTITUTIONAL_WORDS) or \
            (entity and n12 >= config.INSTITUTIONAL_FILINGS)
        large = institutional or any(w in name.upper() for w in config.LARGE_MANAGER_WORDS) or len(props) > 25
        score, signals = 0, []
        b = min(40, 10 * n12); score += b; signals.append(f"{n12} eviction filing(s) (+{b})")
        if n90 >= 2:
            score += 10; signals.append("2+ filings in 90 days (+10)")
        if not entity:
            score += 20; signals.append("individual landlord (+20)")
        if props and len(props) <= 5:
            score += 15; signals.append(f"small landlord: {len(props)} rental address(es) in filings (+15)")
        if out_state and not large:
            score += 10; signals.append(f"landlord address out of state ({mail['state']}) (+10)")
        if large:
            score -= 30; signals.append("institutional / large landlord (-30)" if institutional
                                        else "large manager / complex (-30)")
        score = max(0, min(100, score))
        leads.append({
            "lead_id": hashlib.sha1(k.encode()).hexdigest()[:12],
            "lead_type": "Eviction (tired landlord)",
            "source": "Hamilton County Clerk of Courts - eviction schedules",
            "owner_name": name,
            "owner_type": "entity" if entity else "individual",
            "mailing_street": mail.get("street", ""), "mailing_city": mail.get("city", ""),
            "mailing_state": mail.get("state", ""), "mailing_zip": mail.get("zip", ""),
            "property_addresses": list(props.values())[:50],
            "property_count": len(props),
            "filings_12m": n12, "filings_90d": n90,
            "first_filing": dates[0], "last_filing": dates[-1],
            "case_numbers": sorted(c["case_number"] for c in cs),
            "attorneys": sorted({c.get("plaintiff_attorney", "") for c in cs} - {"", "PRO SE"}),
            "score": score, "tier": "HOT" if score >= 60 else "WARM" if score >= 35 else "COLD",
            "signals": signals,
        })
    leads.sort(key=lambda l: (-l["score"], -l["filings_12m"], l["owner_name"]))
    return leads
