import pandas as pd
import numpy as np

def prepare_fundamentals(fundamentals):
    """
    處理季頻財報資料，計算 US-332 (TTM EPS) 與 US-578 (毛利率 YoY)
    """
    df = fundamentals.copy()
    df["period_end"] = pd.to_datetime(df["period_end"])
    df["published_at"] = pd.to_datetime(df["published_at"])

    # 確保資料依據公司與財報截止日排序，並去重
    df = df.drop_duplicates(subset=["ticker", "period_end"], keep="last")
    df = df.sort_values(["ticker", "period_end"])

    # US-578: 單季毛利率年變動 (取得去年同季資料)
    df["gross_margin_prev_year"] = df.groupby("ticker")["gross_margin"].shift(4)
    df["gross_margin_yoy_diff"] = df["gross_margin"] - df["gross_margin_prev_year"]

    # US-332: 近四季 EPS 滾動加總 (Trailing Twelve Months)
    # min_periods=4 確保新上市未滿一年的公司不會算出錯誤的 TTM
    df["eps_ttm"] = df.groupby("ticker")["eps"].transform(
        lambda x: x.rolling(window=4, min_periods=4).sum()
    )

    return df

def merge_point_in_time(left, right, date_col="published_at", suffix=""):
    """時點對齊合併，嚴格防範前視偏誤 (Look-ahead Bias)"""
    left = left.dropna(subset=["date", "ticker"]).sort_values(["date", "ticker"])
    right = right.dropna(subset=[date_col, "ticker"]).sort_values([date_col, "ticker"])
    right = right.drop_duplicates(subset=[date_col, "ticker"], keep="last")

    result = pd.merge_asof(
        left, right,
        left_on="date", right_on=date_col,
        by="ticker", direction="backward",
        allow_exact_matches=True, suffixes=("", suffix)
    )
    
    # 前視偏誤防呆檢查
    check_col = f"{date_col}{suffix}" if f"{date_col}{suffix}" in result.columns else date_col
    if (result[check_col].notna() & (result[check_col] > result["date"])).any():
        raise ValueError("致命錯誤：檢測到前視偏誤 (Look-ahead bias)！")

    return result