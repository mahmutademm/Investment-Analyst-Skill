# Earnings quality

## 5-step DuPont (Ratios sheet, 5+ years)

ROE = (NI/EBT) x (EBT/EBIT) x (EBIT/Revenue) x (Revenue/Avg assets) x (Avg assets/Avg equity)
= tax burden x interest burden x operating margin x asset turnover x leverage. The workbook proves the
identity: `roe_dupont` equals `roe`.

Ask what is driving ROE:
- Margins and turnover rising -> healthy.
- Leverage rising -> fragile. Heavy buybacks shrink equity and inflate ROE; negative equity makes ROE
  meaningless (the toolkit blanks it).
- Always read ROIC (NOPAT / avg invested capital) alongside ROE: it does not depend on financing.

## Cash vs reported earnings (the most important test)

| Metric | Healthy | Warning |
|---|---|---|
| CFO / net income | ~1.0x or higher, consistently | Persistently < 1: profits not turning into cash |
| Accruals ratio = (NI - CFO) / avg assets | Low, stable | High or rising (Sloan: predicts weaker returns) |
| FCF / net income | Tracks NI | FCF far below NI for years |

## Revenue quality

- **DSO**: receivables growing faster than revenue can mean pulled-forward sales or weak collections
  (`receivables_vs_revenue` > +10pp).
- **Deferred revenue**: shrinking at a subscription business means future revenue is slowing.
- **Revenue-recognition note**: any policy change, new principal/agent judgment, or bill-and-hold.

## Expense quality

- **Capex vs depreciation**: capex far above D&A for years can mean costs are being capitalized. It is
  fine when growth capex is visible.
- **DIO**: rising inventory days can mean weakening demand or a write-down coming.
- **Reserves**: allowance for doubtful accounts falling as a share of receivables, or reserve releases,
  can flatter earnings.
- **SBC % of revenue**: a real cost even when adjusted EPS excludes it. Check the share count trend: are
  buybacks real or just offsetting dilution?

## Non-GAAP vs GAAP

Track adjusted EPS minus GAAP EPS over several years (earnings-release reconciliations). "One-time"
charges that appear every year are recurring costs. Also check whether executive pay depends on those
adjusted numbers (proxy).

## Forensic scores (screens, not verdicts)

| Score | Threshold | Limits |
|---|---|---|
| Beneish M-score (8 variables) | > -1.78 = higher manipulation probability; -2.22 to -1.78 grey | Fast growers and M&A distort SGI/AQI; not for banks |
| Piotroski F-score (0-9) | >= 7 strong, <= 3 weak | Designed for value stocks; loss-making growers score low by construction |
| Sloan accruals | High = weaker future returns | Large acquisitions distort the asset base |
| Altman Z / Z'' | Z > 2.99 safe, < 1.81 distress; Z'' > 2.60 safe, < 1.10 distress | Z for manufacturers; use Z'' otherwise; not for financials |

A bad score is a reason to dig into the filings, not an automatic conclusion. A good score does not clear
a company that has a material weakness or a restatement.
