"""Offline unit tests: python -m unittest discover -s plugins/investment-analyst/toolkit/tests"""
import math
import unittest

import pandas as pd

from iat import company, fundamentals, ratios, valuation


def _flow(start, end, val, form, filed, fp="FY"):
    return {"start": start, "end": end, "val": val, "form": form, "fp": fp, "filed": filed, "accn": f"acc-{filed}"}


def _inst(end, val, form, filed):
    return {"end": end, "val": val, "form": form, "fp": "FY", "filed": filed, "accn": f"acc-{filed}"}


FACTS = {
    "entityName": "TestCo",
    "facts": {
        "dei": {"EntityCommonStockSharesOutstanding": {"units": {"shares": [_inst("2025-07-25", 100, "10-Q", "2025-08-01")]}}},
        "us-gaap": {
            "Revenues": {"units": {"USD": [
                _flow("2023-01-01", "2023-12-31", 1000, "10-K", "2024-02-15"),
                _flow("2023-01-01", "2023-12-31", 1010, "10-K", "2025-02-15"),  # restated comparative
                _flow("2024-01-01", "2024-12-31", 1200, "10-K", "2025-02-15"),
                _flow("2025-01-01", "2025-06-30", 700, "10-Q", "2025-08-01", "Q2"),
                _flow("2025-04-01", "2025-06-30", 360, "10-Q", "2025-08-01", "Q2"),
                _flow("2024-01-01", "2024-06-30", 550, "10-Q", "2025-08-01", "Q2"),
            ]}},
            "NetIncomeLoss": {"units": {"USD": [
                _flow("2023-01-01", "2023-12-31", 100, "10-K", "2025-02-15"),
                _flow("2024-01-01", "2024-12-31", 150, "10-K", "2025-02-15"),
                _flow("2025-01-01", "2025-06-30", 90, "10-Q", "2025-08-01", "Q2"),
                _flow("2024-01-01", "2024-06-30", 70, "10-Q", "2025-08-01", "Q2"),
            ]}},
            "Assets": {"units": {"USD": [
                _inst("2023-12-31", 2000, "10-K", "2025-02-15"), _inst("2024-12-31", 2200, "10-K", "2025-02-15"),
                _inst("2025-06-30", 2300, "10-Q", "2025-08-01")]}},
            "StockholdersEquity": {"units": {"USD": [
                _inst("2023-12-31", 800, "10-K", "2025-02-15"), _inst("2024-12-31", 900, "10-K", "2025-02-15"),
                _inst("2025-06-30", 950, "10-Q", "2025-08-01")]}},
            "LongTermDebt": {"units": {"USD": [
                _inst("2023-12-31", 500, "10-K", "2025-02-15"), _inst("2024-12-31", 450, "10-K", "2025-02-15"),
                _inst("2025-06-30", 440, "10-Q", "2025-08-01")]}},
            "CommercialPaper": {"units": {"USD": [_inst("2024-12-31", 50, "10-K", "2025-02-15")]}},
        },
    },
}


class TestSecParser(unittest.TestCase):
    def setUp(self):
        self.fx = fundamentals.from_sec("TST", FACTS)

    def test_columns_and_restatement(self):
        self.assertEqual(list(self.fx.frame.columns), ["2023-12-31", "2024-12-31", "TTM"])
        self.assertEqual(self.fx.frame.loc["revenue", "2023-12-31"], 1010)  # latest filing wins

    def test_ttm_flow_and_instant(self):
        self.assertEqual(self.fx.frame.loc["revenue", "TTM"], 1200 + 700 - 550)
        self.assertEqual(self.fx.frame.loc["net_income", "TTM"], 150 + 90 - 70)
        self.assertEqual(self.fx.frame.loc["total_assets", "TTM"], 2300)

    def test_total_debt_components(self):
        self.assertEqual(self.fx.frame.loc["total_debt", "2024-12-31"], 450 + 50)
        self.assertEqual(self.fx.frame.loc["total_debt", "2023-12-31"], 500)

    def test_shares_from_cover_page(self):
        self.assertEqual(self.fx.meta["shares_outstanding"]["value"], 100)


class TestRatioEngine(unittest.TestCase):
    def frame(self):
        cols = ["2023", "2024"]
        f = pd.DataFrame(math.nan, index=list(fundamentals.FIELDS), columns=cols, dtype=float)
        f.loc["revenue"] = [100.0, 120.0]
        f.loc["net_income"] = [10.0, 12.0]
        f.loc["pretax_income"] = [13.0, 15.0]
        f.loc["operating_income"] = [15.0, 18.0]
        f.loc["total_assets"] = [200.0, 220.0]
        f.loc["equity"] = [80.0, -5.0]
        return fundamentals.Fundamentals("T", f, f.astype(str))

    def test_growth_and_margin(self):
        t = ratios.evaluate(self.frame())
        self.assertAlmostEqual(t.loc["revenue_growth", "2024"], 0.2)
        self.assertAlmostEqual(t.loc["operating_margin", "2024"], 0.15)
        self.assertTrue(math.isnan(t.loc["revenue_growth", "2023"]))

    def test_negative_equity_blanks_roe(self):
        t = ratios.evaluate(self.frame())
        self.assertAlmostEqual(t.loc["roe", "2024"], 12 / 37.5)  # average equity still positive
        f = self.frame()
        f.frame.loc["equity"] = [-10.0, -5.0]
        t2 = ratios.evaluate(f)
        self.assertTrue(math.isnan(t2.loc["roe", "2024"]))

    def test_excel_formula_guards_missing_inputs(self):
        r = ratios.RATIOS["operating_margin"]
        rows = {k: i + 5 for i, k in enumerate(fundamentals.FIELDS)}
        mrows = {k: i + 5 for i, k in enumerate(ratios.RATIOS)}
        ctx = ratios.XlCtx(rows, mrows, ["C", "D"], 1, set())
        f = ratios.excel_formula(r, ctx)
        self.assertTrue(f.startswith("=IF(COUNT("))
        self.assertIn("Financials!D", f)


class TestValuation(unittest.TestCase):
    def test_reverse_dcf_round_trip(self):
        b = valuation.Base(revenue0=1000, margin0=0.15, tax_rate=0.21, wacc=0.08, net_debt=200, minority=0,
                           shares=100, price=0)
        s = valuation.Scenario("Base", 0.10, 5, 0.025, 0.18, 5, 1.5, 0.10)
        b.price = valuation.dcf(b, s)["per_share"]
        s2 = valuation.Scenario(**{**s.to_dict(), "g1": 0.03})
        r = valuation.reverse_dcf(b, s2)
        self.assertAlmostEqual(r["implied_g1"], 0.10, places=4)

    def test_position_size_respects_caps(self):
        p = valuation.position_size(price=100, atr=2, k=2.5, portfolio=100000, risk_pct=1, max_pct=5)
        self.assertEqual(p["stop"], 95)
        self.assertEqual(p["shares"], 50)  # risk budget allows 200, the 5% cap allows 50
        self.assertTrue(p["capped"])


class TestGate(unittest.TestCase):
    def test_bands(self):
        th = {"cfo_ni_pass": 1.0, "cfo_ni_fail": 0.8}
        spec = company.GATE_SPEC[0]
        self.assertEqual(company.gate_status(1.2, spec, th), "PASS")
        self.assertEqual(company.gate_status(0.9, spec, th), "WATCH")
        self.assertEqual(company.gate_status(0.5, spec, th), "FAIL")
        self.assertEqual(company.gate_status(float("nan"), spec, th), "NO DATA")

    def test_overall(self):
        rows = [{"status": "PASS"}, {"status": "TO REVIEW"}]
        self.assertTrue(company.gate_overall(rows).startswith("INCOMPLETE"))
        self.assertEqual(company.gate_overall([{"status": "PASS"}, {"status": "FAIL"}]), "FAIL")


if __name__ == "__main__":
    unittest.main()
