# Macro sources (primary first)

| Need | Source | URL | Notes |
|---|---|---|---|
| All FRED series used by `iat macro` | FRED, St. Louis Fed | https://fred.stlouisfed.org | Pulled automatically, no key |
| FOMC statements, minutes, SEP / dot plot, meeting calendar | Federal Reserve | https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm | The SEP comes quarterly (Mar/Jun/Sep/Dec) |
| Market-implied rate path | CME FedWatch | https://www.cmegroup.com/markets/interest-rates/cme-fedwatch-tool.html | Probabilities per meeting; may need a browser. Proxy: 2Y minus fed funds |
| CPI detail and release schedule | BLS | https://www.bls.gov/cpi/ | Core services, shelter, goods |
| PCE and GDP | BEA | https://www.bea.gov/data/personal-consumption-expenditures-price-index | Core PCE = Fed target |
| Jobs report schedule and detail | BLS | https://www.bls.gov/ces/ | |
| ISM PMIs (new orders) | ISM | https://www.ismworld.org/supply-management-news-and-reports/reports/ism-report-on-business/ | Not on FRED |
| Sector EPS revisions, forward P/E vs 5y/10y averages | FactSet Earnings Insight (free weekly PDF) | https://insight.factset.com/topic/earnings | **Primary source for pillars 2 and 4** |
| Sector forward P/E history (charts) | Yardeni Research | https://yardeni.com/charts/ | Backup for pillar 4 |
| S&P 500 sector data | S&P Dow Jones Indices | https://www.spglobal.com/spdji/en/ | Earnings and constituent data |
| Equity risk premium (monthly) | Damodaran, NYU Stern | https://pages.stern.nyu.edu/~adamodar/ | Updates `valuation.equity_risk_premium` |
| Leading Economic Index | The Conference Board | https://www.conference-board.org/topics/us-leading-indicators | Headline is free |
| Recession dating | NBER | https://www.nber.org/research/business-cycle-dating | Lagging; confirms only |

Opinion sources (label as opinion): bank strategist outlooks, fund-manager surveys, financial TV.
Do not use as evidence: social media, forums, anonymous newsletters.
