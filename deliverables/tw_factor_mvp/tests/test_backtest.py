import sys, unittest, tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import pandas as pd
from backtest import load_panel, backtest

def panel(nmonths=3):
    rows=[]
    for m in pd.date_range("2022-10-31", periods=nmonths, freq="ME"):
        for i in range(12):
            rows.append({"month":m,"ticker":f"{i:04}","investable":True,"mom_12_1":i,"mom_6_1":i/2,"reversal_1m":i/10,"low_vol_12m":12-i,"liquidity_60d":i+1,"next_return":i/10000,"benchmark_return":.01})
    return pd.DataFrame(rows)

class BacktestTests(unittest.TestCase):
    def test_backtest_returns_costs_and_benchmark(self):
        r,h=backtest(panel(), top_n=5)
        self.assertEqual(len(r),3); self.assertTrue((r.cost>=0).all()); self.assertTrue((r.holdings==5).all())
        self.assertIn("benchmark_return",r); self.assertEqual(len(h),15)
        self.assertGreater(r.turnover_one_way.iloc[0],0)
    def test_no_investable_names_is_safe(self):
        x=panel(1); x["investable"]=False
        r,h=backtest(x,top_n=5)
        self.assertEqual(r.holdings.iloc[0],0); self.assertTrue(h.empty)
    def test_schema_rejects_percent_returns(self):
        x=panel(1); x.loc[0,"next_return"]=15
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"bad.csv"; x.to_csv(p,index=False)
            with self.assertRaises(ValueError): load_panel(p)
if __name__ == "__main__": unittest.main(verbosity=2)
