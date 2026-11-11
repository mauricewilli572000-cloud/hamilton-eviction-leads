import datetime as dt

import evictions as E

SCHED = """<table><tr><td>Judge: EVICTIONS MAGISTRATE</td><td>Location: JC ROOM B</td></tr>
<tr><td>Case #:</td><td>26CV33785</td><td>Time:</td><td>09:15</td></tr>
<tr><td>Plaintiff:</td><td>WILLIAM EDWARDS</td><td>Attorney for Plaintiff:</td><td>PRO SE</td></tr>
<tr><td>Defendant:</td><td>LESLEE PESKIN HUTCHINSON</td><td>Attorney for Defendant:</td><td></td></tr>
<tr><td>Next Action:</td><td>HEARING</td><td></td><td></td></tr></table>"""
PARTY = """Filed Date: </td><td>10/13/2026</td> Case Type: <td>G1-EVICTION</td>
<table><tr><th>Name</th><th>Address</th><th>Party</th><th>Attorney</th></tr>
<tr><td>WILLIAM EDWARDS</td><td>9 ELM ST&nbsp; DALLAS TX 75201</td><td>P&nbsp;1</td><td>PRO SE</td></tr>
<tr><td>LESLEE PESKIN HUTCHINSON</td><td>7053 NOBLE COURT&nbsp; CINCINNATI OH 45239</td><td>D&nbsp;1</td><td></td></tr></table>"""


def test_schedule_and_party():
    cases = E.parse_schedule(SCHED, "2026-11-12")
    assert cases[0]["case_number"] == "26CV33785" and cases[0]["plaintiff"] == "WILLIAM EDWARDS"
    d = E.parse_party(PARTY)
    assert d["filed_date"] == "2026-10-13" and d["defendants"][0]["address"].startswith("7053 NOBLE")


def test_split_addr():
    assert E.split_addr("7053 NOBLE COURT CINCINNATI OH 45239") == {"street": "7053 NOBLE COURT", "city": "Cincinnati", "state": "OH", "zip": "45239"}
    assert E.split_addr("123 MAIN ST APT 4 NORTH COLLEGE HILL OH 45231")["city"] == "North College Hill"


def test_leads():
    c = E.parse_schedule(SCHED, "2026-11-12")[0]
    c["detail"] = E.parse_party(PARTY)
    leads = E.build_leads({c["case_number"]: c}, dt.date(2026, 11, 11))
    l = leads[0]
    assert l["property_addresses"] == ["7053 NOBLE COURT, Cincinnati, OH 45239"]
    assert l["mailing_state"] == "TX" and l["owner_type"] == "individual" and l["tier"] in ("HOT", "WARM")
