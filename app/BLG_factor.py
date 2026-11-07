import pandas as pd
import numpy as np

def calculate_raw_factors(df):
    """計算所有使用者故事中定義的因子"""
    df = df.copy().sort_values(["ticker", "date"])

    # ==========================================
    # US-332: 預估高股息殖利率因子 (est_dividend_yield)
    # ==========================================
    # 預估殖利率 = (TTM EPS * 預估配息率) / 最新收盤價
    est_div_yield = (df["eps_ttm"] * df["dividend_rate"]) / df["close"].replace(0, np.nan)
    
    # 驗收標準 4：若 TTM EPS 為負值，或歷史配息率為 0，預估殖利率直接標記為 0 (淘汰)
    df["factor_est_dividend_yield"] = np.where(
        (df["eps_ttm"] < 0) | (df["dividend_rate"] == 0),
        0.0,
        est_div_yield
    )

    # ==========================================
    # US-496: 投信買超佔股本比因子 (itc_net_buy_ratio)
    # ==========================================
    # 驗收標準 1：必須使用 t-1 日（含）以前的盤後公布數據 (避免偷看今日盤後籌碼)
    df["trust_net_buy_t_1"] = df.groupby("ticker")["trust_net_buy"].shift(1)
    
    # 計算過去 5 日累計買賣超 (遇到 NaN 補 0)
    trust_net_buy_5d = df.groupby("ticker")["trust_net_buy_t_1"].transform(
        lambda x: x.rolling(window=5, min_periods=1).sum()
    ).fillna(0)
    
    # 驗收標準 2 & 3 & 4：除以發行總張數，無交易紀錄時必須為 0 而非 NaN
    df["factor_itc_net_buy_ratio"] = trust_net_buy_5d / df["shares_outstanding"].replace(0, np.nan)
    df["factor_itc_net_buy_ratio"] = df["factor_itc_net_buy_ratio"].fillna(0.0)

    # ==========================================
    # US-578: 單季毛利率年變動因子 (gross_margin_yoy_diff)
    # ==========================================
    # 驗收標準 3：若財報缺漏，維持 NaN (在 data.py 中已處理相減邏輯)
    df["factor_gross_margin_yoy_diff"] = df["gross_margin_yoy_diff"]

    return df

def cross_sectional_zscore(df):
    """計算橫斷面 Z-score 並防範全 NaN 淘汰"""
    df = df.copy()
    factor_cols = [c for c in df.columns if c.startswith("factor_")]
    z_cols = [c.replace("factor_", "z_") for c in factor_cols]

    # Pandas transform 自動忽略 NaN 並按日獨立計算
    df[z_cols] = df.groupby("date")[factor_cols].transform(
        lambda x: (x - x.mean()) / x.std(ddof=1)
    )
    return df

def build_factors(df):
    df = calculate_raw_factors(df)
    df = cross_sectional_zscore(df)
    return df