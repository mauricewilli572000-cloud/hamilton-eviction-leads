#!/usr/bin/env python3
"""Hamilton County eviction leads: eviction schedules -> case party info (cached) -> landlord leads."""
from __future__ import annotations

import csv
import datetime as dt
import json
import logging
import shutil
import sys
import time

import config
import evictions as E

log = logging.getLogger("hamilton_evictions")


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    today = dt.date.today()
    cases = json.loads(config.CASES_JSON.read_text()) if config.CASES_JSON.exists() else {}

    seen = new = 0
    for off in range(-config.DAYS_BACK, config.DAYS_FORWARD + 1):
        day = today + dt.timedelta(days=off)
        if day.weekday() >= 5:
            continue
        try:
            rows = E.fetch_schedule(day)
        except Exception as e:  # noqa: BLE001
            log.warning("schedule %s failed: %s", day, e)
            continue
        for c in rows:
            seen += 1
            old = cases.get(c["case_number"])
            if old is None:
                c["first_seen"] = today.isoformat()
                cases[c["case_number"]] = c
                new += 1
            else:
                old["hearing_date"] = max(old.get("hearing_date", ""), c["hearing_date"])
        time.sleep(config.REQUEST_DELAY)
    log.info("Schedules: %d hearings read, %d new cases, %d cases stored", seen, new, len(cases))

    todo = [k for k, c in cases.items() if not c.get("detail")]
    done = 0
    for k in todo[: config.MAX_CASE_LOOKUPS]:
        try:
            cases[k]["detail"] = E.fetch_case(k)
            done += 1
        except Exception as e:  # noqa: BLE001
            log.warning("case %s failed: %s", k, e)
        time.sleep(config.REQUEST_DELAY)
    log.info("Case details: %d looked up, %d still waiting", done, len(todo) - done)

    leads = E.build_leads(cases, today)
    meta = {"updated_utc": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M"), "cases": len(cases),
            "landlords": len(leads), "hot": sum(1 for l in leads if l["tier"] == "HOT"),
            "rental_addresses": sum(l["property_count"] for l in leads)}
    config.DATA_DIR.mkdir(exist_ok=True)
    config.DOCS_DIR.mkdir(exist_ok=True)
    config.CASES_JSON.write_text(json.dumps(cases, separators=(",", ":")), encoding="utf-8")
    config.DASHBOARD_JSON.write_text(json.dumps({"meta": meta, "records": leads}, separators=(",", ":")), encoding="utf-8")
    with open(config.GHL_CSV, "w", newline="", encoding="utf-8-sig") as fh:
        w = csv.writer(fh)
        w.writerow(["First Name", "Last Name", "Company Name", "Mailing Address", "City", "State", "Postal Code",
                    "Lead Type", "Score", "Tier", "Eviction Filings (12 mo)", "Last Filing", "Rental Addresses",
                    "Property Addresses", "Case Numbers", "Signals", "Tags"])
        for l in leads:
            if not l["property_count"]:
                continue
            if E.is_entity(l["owner_name"]):
                first, last, company = "", "", l["owner_name"].title()
            else:
                parts = l["owner_name"].title().split()
                first, last, company = " ".join(parts[:-1]), parts[-1] if parts else "", ""
            w.writerow([first, last, company, l["mailing_street"], l["mailing_city"], l["mailing_state"],
                        l["mailing_zip"], l["lead_type"], l["score"], l["tier"], l["filings_12m"], l["last_filing"],
                        l["property_count"], " | ".join(l["property_addresses"][:10]), "; ".join(l["case_numbers"][:20]),
                        "; ".join(l["signals"]), f"hamilton-evictions,{l['tier'].lower()},{l['owner_type']}"])
    shutil.copyfile(config.GHL_CSV, config.DOCS_CSV)
    log.info("Saved %d landlord leads (%d hot), %d rental addresses", len(leads), meta["hot"], meta["rental_addresses"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
