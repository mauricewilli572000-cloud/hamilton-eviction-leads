import json, re
from curl_cffi import requests as cr
S = cr.Session(impersonate="chrome")
def show(tag, obj): print(f"@@{tag}@@ " + json.dumps(obj, default=str)[:6000])
p = S.get("https://www.courtclerk.org/records-search/eviction-schedule-search/", timeout=60)
show("checkcc", re.findall(r"function checkcc.*?\n\}", p.text, re.S)[:1] + re.findall(r"recaptcha[^\"']*", p.text)[:5])
for d in ["11/12/2026", "11/10/2026"]:
    r = S.get("https://www.courtclerk.org/data/eviction_schedule.php", params={"chosendate": d, "court": "MCV", "location": "EVIM"}, timeout=60,
              headers={"Referer": "https://www.courtclerk.org/records-search/eviction-schedule-search/"})
    t = r.text
    rows = re.findall(r"<tr[^>]*>(.*?)</tr>", t, re.S)
    cells = [[re.sub(r"<[^>]+>|\s+", " ", c).strip() for c in re.findall(r"<t[hd][^>]*>(.*?)</t[hd]>", x, re.S)] for x in rows]
    show("sched " + d, {"st": r.status_code, "len": len(t), "captcha": bool(re.search(r"captcha", t, re.I)), "rows": len(rows), "cells": cells[:10],
                        "links": re.findall(r'href="([^"]+)"', t)[:15], "text": re.sub(r"<script.*?</script>|<style.*?</style>|<[^>]+>|\s+", " ", t)[:1200]})
