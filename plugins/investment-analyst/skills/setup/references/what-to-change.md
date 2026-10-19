# What to change when the focus changes

Almost everything is driven by three small files in the workspace `config/` folder. Code never needs
editing for a new sector or stock.

## New macro view or new sector weights

Recorded by `/investment-analyst:macro-analysis` in `config/state.yaml`:

```yaml
cycle: {phase: Late cycle, date: 2026-10-18, confidence: Medium}
allocation: {Health Care: 25, Energy: 20, ...}          # % weights, sum to 100
sub_industries: {Health Care: [medical-devices, managed-care], ...}
screening:
  active: [medical-devices, managed-care, oil-gas-ep]   # what the weekly GitHub Action screens
```

Change with `python -m iat state set screening.active "[medical-devices, oil-gas-ep]"` (or let the skill do it).
Commit and push `config/state.yaml` so the weekly Action sees it.

## A sub-industry that is not in the list

Edit `config/sub_industries.yaml`:

1. `python -m iat industries --sector "Health Care"` shows the exact Yahoo industry names.
2. Add an entry:
   ```yaml
   dental:
     name: Dental supplies
     sector: Health Care
     yahoo_industries: ["Medical Instruments & Supplies"]
     etf: null
     profile: standard
     include: [XRAY, ALGN, HSIC]   # when the Yahoo industry is broader than your peer group
     notes: Procedure volumes, consumables mix.
   ```
3. `python -m iat universe dental` and review the list.

Profiles switch the valuation/quality metrics: `standard`, `bank` (P/TBV, ROTCE), `insurer` (P/B, ROE),
`reit` (P/FFO), `energy` (EV/EBITDA, FCF yield, leverage), `early_growth` (EV/sales, growth, rule of 40),
`managed_care` (standard + MLR review).

## A stock in the wrong peer group

Use `exclude:` / `include:` under the sub-industry, or pass peers explicitly in the deep dive:
`python -m iat company XYZ --peers AAA,BBB,CCC,DDD,EEE`.

## Thresholds and portfolio rules

`config/settings.yaml`: `portfolio` (value, positions, risk per position, caps), `screening`
(market cap, dollar volume, how many names get a news check), `thresholds` (gate pass/fail levels),
`valuation` (equity risk premium, terminal growth, ATR multiple, scenario probabilities). Refresh the
equity risk premium monthly from Damodaran's implied ERP page.

## After a plugin update

```
python -m pip install --upgrade "<plugin folder>/toolkit"
python -m iat upgrade      # refreshes .toolkit/ and .github/workflows/ in the workspace
```
Commit and push so GitHub Actions use the same toolkit version.
