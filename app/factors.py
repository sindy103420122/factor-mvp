"""因子計算。對應 requirements/US-101、US-102。"""
import numpy as np
import pandas as pd


def revenue_yoy(revenue: pd.DataFrame, asof: str) -> pd.DataFrame:
    """回傳每檔股票在 asof 當天「已公布」的最新月營收年增率。

    revenue 欄位：stock_id, month (YYYY-MM), revenue, publish_date
    回傳欄位：stock_id, month_used, yoy（缺值為 NaN，不補 0）
    """
    asof_ts = pd.Timestamp(asof)
    df = revenue.copy()
    df["publish_date"] = pd.to_datetime(df["publish_date"])

    # 對應 Scenario: 公布前使用上一個月營收（只用公布日 <= asof 的資料）
    visible = df[df["publish_date"] <= asof_ts]

    rows = []
    for stock_id, g in visible.groupby("stock_id"):
        latest = g.sort_values("month").iloc[-1]
        month_used = latest["month"]
        last_year = str(pd.Period(month_used, "M") - 12)
        # 去年同月資料也必須是 asof 前已公布（此處以 visible 篩選後的資料查找）
        prev = g[g["month"] == last_year]
        if prev.empty or prev.iloc[0]["revenue"] <= 0:
            # 對應 Scenario: 缺少去年同月資料時為缺值（不補 0）
            # 去年同月營收 <= 0 時年增率無意義，也視為缺值
            yoy = float("nan")
        else:
            yoy = latest["revenue"] / prev.iloc[0]["revenue"] - 1
        rows.append({"stock_id": stock_id, "month_used": month_used, "yoy": yoy})
    return pd.DataFrame(rows, columns=["stock_id", "month_used", "yoy"])


def to_wide_prices(prices: pd.DataFrame) -> pd.DataFrame:
    """長表（stock_id, date, adj_close）轉成寬表（index=date, columns=stock_id）。"""
    p = prices.copy()
    p["date"] = pd.to_datetime(p["date"])
    return p.pivot_table(index="date", columns="stock_id", values="adj_close").sort_index()


def momentum_12_1(wide_prices: pd.DataFrame, asof: str) -> pd.Series:
    """12-1 個月動能 = P(t-1 月) / P(t-12 月) - 1。對應 US-102。

    wide_prices：index=date, columns=stock_id 的還原收盤價。
    回傳：index=stock_id 的 Series，缺值為 NaN。
    """
    asof_ts = pd.Timestamp(asof)
    # 對應 Scenario: 計算日之後的價格不影響結果（先切掉 asof 之後的資料）
    hist = wide_prices.loc[:asof_ts]
    t1 = asof_ts - pd.DateOffset(months=1)
    t12 = asof_ts - pd.DateOffset(months=12)

    # 「前 N 個月」取當天或之前最近一個有價格的交易日（AC3）
    def last_on_or_before(t):
        part = hist.loc[:t]
        if part.empty:
            return pd.Series(np.nan, index=hist.columns)
        return part.ffill().iloc[-1]

    p1, p12 = last_on_or_before(t1), last_on_or_before(t12)
    # 對應 Scenario: 上市未滿 12 個月時動能為缺值（p12 為 NaN，相除後自然為 NaN）
    mom = p1 / p12 - 1
    mom.name = "momentum_12_1"
    return mom


def cross_section_zscore(s: pd.Series, lower: float = 0.01, upper: float = 0.99) -> pd.Series:
    """橫斷面標準化：先 Winsorize（1%／99%），再做 z-score。缺值保持缺值。"""
    valid = s.dropna()
    if len(valid) < 3:
        return pd.Series(np.nan, index=s.index)
    lo, hi = valid.quantile(lower), valid.quantile(upper)
    clipped = s.clip(lo, hi)
    std = clipped.std()
    if std == 0 or np.isnan(std):
        return pd.Series(0.0, index=s.index).where(s.notna())
    return (clipped - clipped.mean()) / std
