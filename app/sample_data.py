"""產生「假資料」，讓沒有 TEJ 權限的電腦也能一行指令跑完整條管線。

這些數字是模擬出來的，不代表任何真實股票，績效也沒有意義，只用來確認流程可以跑通。
固定亂數種子，確保每次產生的資料都一樣（可重現）。
"""
from pathlib import Path

import numpy as np
import pandas as pd


def generate(folder: str, n_stocks: int = 80, seed: int = 42) -> None:
    rng = np.random.default_rng(seed)
    days = pd.bdate_range("2013-01-01", "2022-12-31")
    months = pd.period_range("2012-01", "2022-12", freq="M")
    ids = [str(1101 + i * 7) for i in range(n_stocks)]

    # 每檔股票有一個隨時間緩慢變化的「體質」g，同時影響營收成長與未來股價
    g = np.zeros((len(months), n_stocks))
    for t in range(1, len(months)):
        g[t] = 0.9 * g[t - 1] + rng.normal(0, 0.3, n_stocks)

    rev_rows, base = [], rng.uniform(100, 5000, n_stocks)
    level = base.copy()
    for t, m in enumerate(months):
        season = 1 + 0.1 * np.sin(2 * np.pi * m.month / 12)
        level = level * np.exp(0.01 * g[t] + rng.normal(0, 0.03, n_stocks))
        pub = (m + 1).to_timestamp() + pd.to_timedelta(rng.integers(4, 10, n_stocks), "D")
        for j, s in enumerate(ids):
            rev_rows.append((s, str(m), round(level[j] * season, 2), pub[j].date()))
    revenue = pd.DataFrame(rev_rows, columns=["stock_id", "month", "revenue", "publish_date"])

    # 日報酬：市場共同部分 + 由「已公布體質」帶來的小幅漂移 + 個股雜訊
    month_idx = np.searchsorted(months.to_timestamp().values, days.values, side="right") - 2
    month_idx = np.clip(month_idx, 0, len(months) - 1)
    mkt = rng.normal(0.0003, 0.01, len(days))
    drift = 0.0006 * g[month_idx]
    rets = mkt[:, None] + drift + rng.normal(0, 0.018, (len(days), n_stocks))
    rets = np.clip(rets, -0.1, 0.1)
    adj = 50 * np.exp(np.cumsum(np.log1p(rets), axis=0))

    # 成交金額：少數股票刻意設為流動性不足
    liq = rng.lognormal(np.log(1.5e8), 1.0, n_stocks)
    liq[:8] = rng.uniform(2e6, 1.2e7, 8)
    value = liq[None, :] * rng.lognormal(0, 0.3, (len(days), n_stocks))

    prices = pd.DataFrame({
        "stock_id": np.repeat([ids], len(days), axis=0).ravel(),
        "date": np.repeat(days.date, n_stocks),
        "adj_close": adj.ravel().round(4),
        "trade_value": value.ravel().round(0),
        "limit_up": (rets >= 0.095).ravel(),
    })
    # 一檔在 2019-06 下市（之後沒有價格），一檔在 2017-03 才上市
    delisted, late = ids[10], ids[11]
    prices = prices[~((prices["stock_id"] == delisted) & (pd.to_datetime(prices["date"]) > "2019-06-14"))]
    prices = prices[~((prices["stock_id"] == late) & (pd.to_datetime(prices["date"]) < "2017-03-01"))]

    listing = pd.DataFrame({"stock_id": ids, "list_date": "2000-01-01", "delist_date": pd.NA})
    listing.loc[listing["stock_id"] == delisted, "delist_date"] = "2019-06-15"
    listing.loc[listing["stock_id"] == late, "list_date"] = "2017-03-01"

    bench = pd.DataFrame({"date": days.date, "close": (10000 * np.cumprod(1 + mkt + 0.00012)).round(2)})

    out = Path(folder)
    out.mkdir(parents=True, exist_ok=True)
    prices.to_csv(out / "prices.csv", index=False)
    revenue.to_csv(out / "revenue.csv", index=False)
    listing.to_csv(out / "listing.csv", index=False)
    bench.to_csv(out / "benchmark.csv", index=False)
