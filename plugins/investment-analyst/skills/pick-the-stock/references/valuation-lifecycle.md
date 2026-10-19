# Valuation by life cycle

| Stage | Primary method | Workbook location | Notes |
|---|---|---|---|
| Early / unprofitable | EV/sales vs peers, reverse DCF | Valuation (relative block), Reverse DCF | A forward DCF is mostly guesswork |
| High growth | 3-stage DCF | Valuation (scenario blocks) | Stage-1 growth fades linearly to terminal by year 10 |
| Mature | 2-stage DCF, FCF yield | Valuation; set `n1` = 10 or a short fade | Your most reliable DCF case |
| Mature dividend payer | DDM (2-stage / Gordon) | Valuation (DDM block) | Only when the payout is stable |
| Financials | Residual income, justified P/B = (ROE - g) / (Ke - g) | Valuation (financials block) | DCF does not work for banks: debt is their raw material |
| Cyclicals | DCF or multiples on normalized mid-cycle earnings | Valuation (normalized EPS) | Peak earnings make a cyclical look cheap at the worst time |
| Declining | Sum-of-the-parts, liquidation value | Build by hand | Toolkit gives inputs only |

## DCF mechanics in the workbook (FCFF)

- Revenue: base = TTM (or last FY). Years 1..n1 grow at `g1`, then fade linearly to `g_terminal` by year 10.
- EBIT margin: moves linearly from today's margin to `margin_target` by `margin_years`.
- NOPAT = EBIT x (1 - tax). Reinvestment = change in revenue / `sales_to_capital`.
  FCFF = NOPAT - reinvestment.
- Terminal: FCFF(11) = NOPAT(11) x (1 - g / `ronic`); TV = FCFF(11) / (WACC - g). Setting RONIC = WACC
  means growth adds no value beyond year 10, which is a conservative default.
- WACC: Ke = rf (10Y, FRED) + beta x ERP (settings; update monthly from Damodaran). Kd = max(interest /
  avg debt, rf + 1%). Market-value equity weights, book debt including leases.
- Equity value = EV - net debt (incl. leases) - non-controlling interest; per share = equity / shares.

## Assumption discipline

- Anchor `g1` on consensus revenue/EPS growth and the 3-year history; explain any departure using a
  SWOT item.
- Anchor `margin_target` on the company's own 5-year range and the peer median. Moving above both needs
  a moat argument.
- `sales_to_capital` defaults to revenue / invested capital today; capital-light businesses run higher.
- Probabilities sum to 100%. A 25/50/25 split is a default, not a belief. Change it only with a reason.

## Reverse DCF: what is priced in

The Reverse DCF sheet runs the base model across stage-1 growth from -10% to +40% and highlights the row
closest to today's price. Ask whether that growth is realistic compared with consensus and history. If
the market already prices more than the bull case, the 6-month upside is thin whatever the base value says.

## Scenarios, sensitivity and terminal value

Show bull/base/bear and the probability-weighted value. Read the WACC x g grid. If the terminal value is
more than ~70% of EV, the answer depends mostly on the distant future, so trust it less (the sheet warns).

## Relative value done properly

- Peers = the full sub-industry group (5-10), **median** not mean, plus the stock's own history.
- PEG = forward P/E / consensus 2-3 year EPS growth; ignore it when growth is low or negative.
- Add EV/EBITDA and EV/EBIT: P/E ignores debt, and two equal P/Es can carry very different leverage.

## Horizon mismatch

A stock can be 30% undervalued and stay that way for two years. With a 6-month horizon, intrinsic value
gives the margin of safety, and the **catalyst** is what makes the gap close inside the window. The
Decision sheet combines both via the gap-closure input (default 50% with a dated catalyst, 20% without).
