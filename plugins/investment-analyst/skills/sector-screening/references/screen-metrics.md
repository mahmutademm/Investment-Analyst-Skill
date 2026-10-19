# Screen metrics (all ranked against sub-industry peers, never the whole market)

Thresholds are starting points in `config/settings.yaml`, not rules.

| Category | Indicator | Toolkit column | Starting filter / what to look for |
|---|---|---|---|
| Tradability | Market cap, average daily dollar volume | `market_cap`, `adv_usd_20d` | > ~$2B and > ~$20M/day so entries and stops actually fill (universe filter) |
| Valuation | Forward P/E | `fwd_pe` | Below sub-industry median |
| Valuation | Own history | `pe_vs_own_hist` | Trailing P/E below its median at the last 4-5 fiscal year-ends (GAAP EPS) |
| Valuation | EV/EBITDA, EV/EBIT | `ev_ebitda`, `ev_ebit` | Below median; EV-based multiples put leverage on equal footing |
| Valuation | PEG | `peg` | Forward P/E / consensus 2-year EPS CAGR; **blank when growth < 3%** (meaningless) |
| Valuation | FCF yield | `fcf_yield` | Higher is better |
| Expectations | EPS revisions FY+1, 30 and 90 days | `eps_rev_30d`, `eps_rev_90d` | Rising; avoid names whose estimates are being cut |
| Expectations | Up vs down revisions (30 days) | `net_revisions_30d` | (up - down) / (up + down) > 0 |
| Expectations | Earnings surprises | `beats_4q`, `avg_surprise_pct` | Consistent beats over 4 quarters |
| Expectations | Coverage and dispersion | `analysts`, `estimate_dispersion` | 5+ analysts; (high - low) / mean > 30% = high uncertainty |
| Quality | ROIC, ROE | `roic`, `roe` | Above peers and stable; ROE blank when equity is negative |
| Quality | Margin stability | `op_margin_std` | Lower = more stable (4-year std of EBIT margin) |
| Quality | Cash conversion | `cfo_to_ni`, `fcf_to_ni`, `accruals_ratio` | CFO/NI ~ >= 1; positive TTM FCF; low accruals |
| Balance sheet | Net debt/EBITDA, interest cover | `net_debt_to_ebitda`, `interest_coverage` | < ~3x and > ~4x for non-financials |
| Momentum | 6-12 month return vs ETF; price vs 200-day | `rel_6m_vs_etf`, `rel_12m_vs_etf`, `price_vs_200d` | Not in a persistent downtrend; ideally starting to outperform |
| Risk flags | Short interest, earnings date, 8-K items | `short_pct_float`, `days_to_earnings`, flags | High short interest or binary events need extra scrutiny |
| Forensic | Accruals, Beneish M-score, Piotroski F | `accruals_ratio`, `beneish_m`, `piotroski_f` | Quick earnings-quality red flags before trusting the numbers |

## Ranking

For each metric: percentile within the sub-industry (direction-adjusted). Group score = mean of available
percentiles (needs at least half the group's metrics). Composite = mean of **valuation**, **quality** and
**revisions/momentum** (all three required). Value alone finds traps, momentum alone finds expensive
stocks, and quality alone ignores price; combining them is the point.

## Profiles: sectors where P/E misleads

| Profile | Valuation metrics | Quality metrics | Read manually in the news check / deep dive |
|---|---|---|---|
| `bank` | P/TBV, fwd P/E, own history | ROTCE, ROA | CET1, NPLs, NIM, loan/deposit, CRE exposure, unrealized securities losses |
| `insurer` | P/B, fwd P/E | ROE, ROA | Combined ratio, reserve development, catastrophe exposure |
| `reit` | P/FFO (approx = NI + D&A), EV/EBITDA, dividend yield | EBIT margin, leverage | AFFO, occupancy, lease spreads, maturities |
| `energy` | EV/EBITDA, FCF yield, fwd P/E | ROIC, leverage, CFO/NI | Breakeven oil price, hedges, reserve life |
| `early_growth` | EV/sales, EV/sales per point of growth | Gross margin, revenue growth, Rule of 40, SBC % | Cash runway, dilution |
| `managed_care` | fwd P/E, PEG, own history, FCF yield | ROE, ROIC, margin stability | **Medical loss ratio trend**, days claims payable, rate notices |

## Data caveats to state when presenting

Yahoo data is unofficial and uses vendor definitions (EBITDA, debt incl. leases). The own-history P/E uses
only 4-5 fiscal year-ends. Revisions come from Yahoo's consensus snapshot; cross-check important names on
Zacks (revisions, surprise history) or Koyfin (estimates) before the deep dive.
