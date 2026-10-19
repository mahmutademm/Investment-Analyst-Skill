# notes.json for a company (output/companies/<T>/notes.json)

Create it with `python -m iat notes-template company <T>`, then fill it in. Python renders it into green
cells. Keep it valid JSON (no comments, no trailing commas). Unknown values: `null` or `"unknown"`.

```json
{
  "as_of": "2026-10-19",
  "lifecycle": {"stage": "High growth", "rationale": "Revenue CAGR 17%, profitable, reinvesting", "confirmed_by_user": true},
  "business": {
    "description": "Two or three sentences: what it sells, to whom, how it makes money.",
    "segments": [{"name": "Cardiovascular", "revenue_share": 0.62, "profit_share": 0.70,
                  "comment": "Electrophysiology growing 20%+", "source": "10-K FY2025, Note 18 Segments"}]
  },
  "moat": [{"factor": "Switching costs", "rating": "Moderate", "evidence": "Physician training on platform",
            "numbers": "ROIC 10-12% vs peer median 8% (FY2021-25)", "source": "10-K Item 1; Ratios sheet"}],
  "swot": [{"type": "T", "item": "Reimbursement cuts for procedure X", "evidence": "CMS proposed rule, Jul 2026",
            "source": "cms.gov, 2026-07-12", "assumption": "g1", "direction": "-", "scenario": "Bear"}],
  "bear_case": ["Competitor launch takes share in the core franchise", "Margin target slips on mix"],
  "premortem": ["Q4 guide cut on hospital capex; stock -25% as the multiple compresses to the peer median"],
  "thesis_stops": ["FY+1 EPS revisions negative two months running", "EP share < 40% (company disclosure)"],
  "filing_review": [{"section": "Auditor report / CAMs", "finding": "CAM on revenue reserves for returns",
                     "risk": "Medium", "source": "10-K FY2025, Report of Independent Registered Public Accounting Firm",
                     "quote": "short quote"}],
  "gate_review": [{"test": "Auditor opinion / going-concern language", "status": "PASS",
                   "evidence": "Unqualified opinion, no going-concern paragraph (10-K p.62)"},
                  {"test": "Material weakness in internal control (Item 9A)", "status": "PASS",
                   "evidence": "Management concluded ICFR effective (10-K Item 9A)"}],
  "non_gaap": [{"period": "Q2 2026", "gaap_eps": 0.62, "adjusted_eps": 0.86,
                "main_adjustments": "amortization, restructuring", "recurring": "Yes",
                "source": "8-K 2026-07-23 EX-99.1"}],
  "catalysts": [{"event": "Q3 earnings + FY guide", "date": "2026-10-28", "within_window": "Yes",
                 "impact": "Guide reset could re-rate if EP growth holds", "source": "IR calendar"}],
  "assumptions": {
    "Base": {"g1": 0.10, "margin_target": 0.21},
    "Bear": {"g1": 0.05, "margin_target": 0.18},
    "Bull": {"g1": 0.14, "margin_target": 0.23},
    "rationale": {"g1": "Consensus 2y revenue CAGR 9-11%; 3y history 17% includes M&A",
                  "margin_target": "5y range 16-20%; mix shift to EP (SWOT S1)"}
  },
  "sources": [{"type": "Filing", "title": "10-K FY2025", "url": "https://www.sec.gov/...", "retrieved": "2026-10-19"}]
}
```

`gate_review[].test` must match a test name on the Gate sheet exactly (copy it from `summary.md`).
Allowed statuses: PASS, WATCH, FAIL, TO REVIEW, N/A.

Assumption keys you may set per scenario: `g1`, `n1`, `g_terminal`, `margin_target`, `margin_years`,
`sales_to_capital`, `ronic`, `wacc_adj`, `probability`. Anything you leave out keeps the toolkit default.
