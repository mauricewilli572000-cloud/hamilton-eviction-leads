import json, re, urllib.parse
from curl_cffi import requests as cr
S = cr.Session(impersonate="chrome")
def show(tag, obj): print(f"@@{tag}@@ " + json.dumps(obj, default=str)[:6000])
r = S.get("https://www.courtclerk.org/records-search/", timeout=60)
links = sorted({urllib.parse.urljoin(str(r.url), h) for h in re.findall(r'href="([^"]+)"', r.text) if re.search(r"evict|schedule|address", h, re.I)})
show("links", {"st": r.status_code, "captcha": bool(re.search(r"recaptcha|captcha|turnstile", r.text, re.I)), "links": links})
for u in links[:6]:
    p = S.get(u, timeout=60); t = p.text
    forms = re.findall(r"<form.*?</form>", t, re.S)
    show("page " + u, {"st": p.status_code, "captcha": bool(re.search(r"recaptcha|g-recaptcha|turnstile|hcaptcha", t, re.I)),
         "forms": [{"tag": re.search(r"<form[^>]*>", f).group(0), "inputs": re.findall(r"<(?:input|select)[^>]*>", f)[:15],
                    "options": re.findall(r"<option[^>]*>([^<]*)", f)[:20]} for f in forms[:3]],
         "iframes": re.findall(r'<iframe[^>]+src="([^"]+)"', t)})
