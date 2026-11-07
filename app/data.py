"""載入標準化後的資料。對應管線第一段 data。

標準格式（data/processed/ 底下的四個 CSV，由 app/tej_convert.py 或 app/sample_data.py 產生）：
  prices.csv     stock_id, date, adj_close, trade_value, limit_up
  revenue.csv    stock_id, month, revenue, publish_date
  listing.csv    stock_id, list_date, delist_date
  benchmark.csv  date, close
其他模組只認這個格式，資料來源換了只需要改轉檔，不用改因子與回測。
"""
from dataclasses import dataclass
from pathlib import Path

import pandas as pd


@dataclass
class MarketData:
    wide_prices: pd.DataFrame     # index=date, columns=stock_id（還原收盤價）
    trade_value: pd.DataFrame     # 同上，每日成交金額（元）
    limit_up: pd.DataFrame        # 同上，True 表示當日漲停
    revenue: pd.DataFrame         # 長表
    listing: pd.DataFrame
    benchmark: pd.Series          # index=date


def load_processed(folder: str) -> MarketData:
    d = Path(folder)
    prices = pd.read_csv(d / "prices.csv", dtype={"stock_id": str}, parse_dates=["date"])
    revenue = pd.read_csv(d / "revenue.csv", dtype={"stock_id": str, "month": str})
    listing = pd.read_csv(d / "listing.csv", dtype={"stock_id": str})
    bench = pd.read_csv(d / "benchmark.csv", parse_dates=["date"]).set_index("date")["close"].sort_index()

    def wide(col):
        return prices.pivot_table(index="date", columns="stock_id", values=col, aggfunc="last").sort_index()

    lu = wide("limit_up").fillna(0).astype(bool) if "limit_up" in prices else None
    return MarketData(wide("adj_close"), wide("trade_value"), lu, revenue, listing, bench)
