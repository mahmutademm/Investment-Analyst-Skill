"""Skeletons for the JSON notes the AI writes. Python renders them into the Excel workbooks.

Rules for every note: cite a source (document + section, or URL + date) for each factual claim,
write "unknown" instead of guessing, and keep numbers you did not compute out of the notes.
"""
from __future__ import annotations

MACRO = {
    "as_of": "YYYY-MM-DD",
    "cycle_call": {"phase": "Early recovery | Mid cycle | Late cycle | Contraction",
                   "confidence": "Low | Medium | High", "rationale": "", "confirmed_by_user": False},
    "fed_path": {"market_implied": "e.g. 2 cuts priced by June (CME FedWatch, date)",
                 "fed_dots": "e.g. SEP median 3.4% end-2027 (Fed, date)"},
    "sectors": {
        "Health Care": {
            "revisions": {"direction": "up | flat | down", "value": "e.g. CY+1 EPS est. +1.2% over 3 months",
                          "source": "FactSet Earnings Insight, YYYY-MM-DD"},
            "valuation": {"supportive": "yes | no | neutral",
                          "value": "e.g. fwd P/E 17.1 vs 10y avg 16.9; relative to S&P 0.78 vs 10y avg 0.90",
                          "source": ""},
            "priced_in": "e.g. consensus overweight, premium near 10y high -> limited upside",
            "cycle_fit_override": None,
        }
    },
    "allocation": {"Health Care": 25},
    "sub_industries": {"Health Care": ["medical-devices", "managed-care"]},
    "events": [{"date": "YYYY-MM-DD", "event": "FOMC", "why_it_matters": "", "source": ""}],
    "sources": [{"title": "", "url": "", "retrieved": "YYYY-MM-DD"}],
}

SCREEN = {
    "as_of": "YYYY-MM-DD",
    "news_check": [{
        "ticker": "",
        "why_cheap": "One or two sentences: what the market is worried about",
        "classification": "Temporary | Structural | Unclear",
        "evidence": "Facts with dates (last two earnings releases, 8-Ks, headlines)",
        "catalyst": "", "catalyst_date": "YYYY-MM-DD or window", "catalyst_within_window": "Yes | No",
        "red_flags": "", "deep_dive_candidate": "Yes | No | Your call",
        "sources": ["url or filing reference"],
    }],
    "user_shortlist": [],
}

COMPANY = {
    "as_of": "YYYY-MM-DD",
    "lifecycle": {"stage": "Early / unprofitable | High growth | Mature | Mature dividend payer | Financials | Cyclical | Declining",
                  "rationale": "", "confirmed_by_user": False},
    "business": {"description": "", "segments": [{"name": "", "revenue_share": None, "profit_share": None,
                                                  "comment": "", "source": "10-K Note X (Segments)"}]},
    "moat": [{"factor": "Switching costs | Scale | Network effects | Brand | Regulatory | Intangibles",
              "rating": "Strong | Moderate | Weak | None", "evidence": "", "numbers": "ROIC vs peers 5y: ...",
              "source": ""}],
    "swot": [{"type": "S | W | O | T", "item": "", "evidence": "", "source": "",
              "assumption": "g1 | margin_target | sales_to_capital | ronic | wacc_adj | probability",
              "direction": "+ | -", "scenario": "Bear | Base | Bull | All"}],
    "bear_case": ["Write this FIRST"],
    "premortem": ["It is 6 months later and the stock is down 25%: ..."],
    "thesis_stops": ["e.g. FY+1 EPS revisions turn negative for 2 consecutive months"],
    "filing_review": [{"section": "MD&A critical estimates | Segment note | Contingencies | Debt note | Auditor report / CAMs | "
                                  "Item 9A | Revenue recognition | Related parties | Proxy pay metrics",
                       "finding": "", "risk": "Low | Medium | High", "source": "10-K FY2025, Note 9", "quote": ""}],
    "gate_review": [{"test": "Auditor opinion / going-concern language", "status": "PASS | WATCH | FAIL",
                     "evidence": "Unqualified opinion by <auditor>, no going-concern paragraph (10-K p.XX)"}],
    "non_gaap": [{"period": "", "gaap_eps": None, "adjusted_eps": None, "main_adjustments": "", "recurring": "Yes | No",
                  "source": "8-K EX-99.1 YYYY-MM-DD"}],
    "catalysts": [{"event": "", "date": "", "within_window": "Yes | No", "impact": "", "source": ""}],
    "assumptions": {
        "Base": {"g1": None, "margin_target": None},
        "Bear": {}, "Bull": {},
        "rationale": {"g1": "Why, tied to SWOT items and consensus", "margin_target": ""},
    },
    "sources": [{"type": "Filing | News | Data", "title": "", "url": "", "retrieved": "YYYY-MM-DD"}],
}
