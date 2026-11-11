# Hamilton County (Cincinnati), OH — Eviction Leads (tired landlords)

Built like `franklin-eviction-leads`.

- **Source:** Hamilton County Clerk of Courts (courtclerk.org), Municipal Civil eviction hearing
  schedules (last 45 days + next 3 weeks, re-read daily). Each new case's party page is looked up
  once (cached): the **defendant's address is the rental being evicted**, the plaintiff's address is
  the landlord's mailing address.
- One lead per landlord, listing the rental addresses from their filings. The Cincinnati Metropolitan
  Housing Authority, the City and the land bank are left out.
- Score: repeat filings, individual landlords, small landlords (1–5 rentals), out-of-state landlords;
  large managers / complexes lose points. Requests are spaced about 1 per second.

Outputs: `docs/index.html` · `docs/hamilton_evictions.json` (read by ohio-lead-stacker) ·
`data/ghl_hamilton_evictions.csv`.
