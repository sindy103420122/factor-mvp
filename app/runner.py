"""一行指令跑完整條管線：data → factors → portfolio → backtest → report。

用法：
  python -m app.runner --demo                    # 用假資料跑（任何電腦都能跑）
  python -m app.runner --data data/processed     # 用轉好的 TEJ 資料跑
"""
import argparse
from pathlib import Path

import pandas as pd

from app.backtest import run_backtest
from app.config import Settings, check_period
from app.data import load_processed
from app.factors import momentum_12_1, revenue_yoy
from app.portfolio import combine_scores, select_top_n
from app.report import format_summary, summarize
from app.universe import build_universe


def make_signal_fn(md, settings: Settings):
    def signal(asof):
        universe = build_universe(md.trade_value, md.listing, asof,
                                  settings.min_avg_value, settings.liquidity_lookback)
        if not universe:
            return {}
        rev = revenue_yoy(md.revenue[md.revenue["stock_id"].isin(universe)], asof)
        factors = pd.DataFrame(index=universe)
        factors["revenue_yoy"] = rev.set_index("stock_id")["yoy"].reindex(universe)
        factors["momentum_12_1"] = momentum_12_1(md.wide_prices[universe], asof).reindex(universe)
        score = combine_scores(factors[list(settings.factors)], settings.factor_weights)
        return select_top_n(score, settings.top_n)
    return signal


def main(argv=None):
    ap = argparse.ArgumentParser(description="台股多因子 baseline 回測")
    ap.add_argument("--data", default="data/processed", help="標準化資料夾")
    ap.add_argument("--demo", action="store_true", help="先產生假資料到 data/demo 再執行")
    ap.add_argument("--out", default="output", help="輸出資料夾")
    args = ap.parse_args(argv)

    settings = Settings()
    check_period(settings.end, settings)   # 樣本外鎖

    folder = args.data
    if args.demo:
        from app.sample_data import generate
        folder = "data/demo"
        if not Path(folder, "prices.csv").exists():
            print("產生假資料中（只需一次）...")
            generate(folder)

    md = load_processed(folder)
    monthly, trade_log = run_backtest(make_signal_fn(md, settings), md.wide_prices, settings.cost,
                                      settings.start, settings.end, md.limit_up, md.benchmark)
    summary = summarize(monthly)

    out = Path(args.out)
    out.mkdir(exist_ok=True)
    monthly.to_csv(out / "monthly.csv", index=False)
    pd.DataFrame(trade_log).to_csv(out / "trade_log.csv", index=False)
    pd.Series(summary).to_csv(out / "summary.csv", header=["value"])

    if args.demo:
        print("【注意】以下為假資料結果，只用來確認流程，不代表任何真實績效。")
    print(format_summary(summary))
    print(f"\n明細已輸出到 {out}/（monthly.csv、trade_log.csv、summary.csv）")


if __name__ == "__main__":
    main()
