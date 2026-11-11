import json, re
from curl_cffi import requests as cr
S = cr.Session(impersonate="chrome")
def show(tag, obj): print(f"@@{tag}@@ " + json.dumps(obj, default=str)[:5000])
def txt(t): return re.sub(r"<script.*?</script>|<style.*?</style>|<[^>]+>|\s+", " ", t)
for sec in ["sched", "summary", "party", "docket"]:
    r = S.post("https://www.courtclerk.org/data/case_summary.php", data={"casenumber": "26CV33785", "validate_case_number": "1", "sec": sec}, timeout=60,
               headers={"Referer": "https://www.courtclerk.org/records-search/case-schedules/"})
    t = txt(r.text); i = t.find("26CV33785")
    show("summary " + sec, {"st": r.status_code, "captcha_word": "captcha" in t.lower(), "snip": t[max(0, i - 200): i + 2500] if i >= 0 else t[-1500:]})
p = S.get("https://www.courtclerk.org/records-search/search-by-case-number/", timeout=60)
show("case search page", {"st": p.status_code, "forms": [re.search(r"<form[^>]*>", f).group(0) + " " + " ".join(re.findall(r"<input[^>]*>", f)[:8]) for f in re.findall(r"<form.*?</form>", p.text, re.S)][:3]})
