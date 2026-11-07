import numpy as np
import pandas as pd

def get_rebalance_dates(df):
    """取得資料集內每個月最後一個交易日"""
    dates = pd.to_datetime(df["date"]).drop_duplicates().sort_values()
    return dates.groupby(dates.dt.to_period("M")).max().tolist()

def build_portfolio(df, top_n=20, min_score=None):
    """
    智慧選股投資組合 (Smart Beta)：月調倉，依合成分數選 Top N，等權重配置
    """
    df = df.copy()
    df["date"] = pd.to_datetime(df["date"])

    # 1. 批次篩選出所有調倉日且訊號非 NaN 的資料
    rebalance_dates = get_rebalance_dates(df)
    reb_df = df[df["date"].isin(rebalance_dates)].dropna(subset=["signal_score"])

    # 2. 分數門檻過濾
    if min_score is not None:
        reb_df = reb_df[reb_df["signal_score"] >= min_score]

    # 3. 向量化選股：依日期與分數排序後，取每期前 top_n 檔
    portfolio = (
        reb_df.sort_values(["date", "signal_score"], ascending=[True, False])
        .groupby("date", as_index=False)
        .head(top_n)
        .copy()
    )

    # 若全無選出標的，回傳安全的空 DataFrame
    if portfolio.empty:
        return pd.DataFrame(columns=["rebalance_date", "date", "ticker", "signal_score", "weight"])

    # 4. 計算等權重（依每期實際入選檔數平分 1.0）
    portfolio["weight"] = 1.0 / portfolio.groupby("date")["ticker"].transform("count")
    portfolio["rebalance_date"] = portfolio["date"]

    valid_cols = [c for c in ["rebalance_date", "date", "ticker", "signal_score", "close", "weight"] if c in portfolio.columns]
    return portfolio[valid_cols].reset_index(drop=True)

def build_baseline_portfolio(df):
    """
    基準對照組 (Baseline)：月調倉，全市場等權重，作為計算 Alpha 比較用
    """
    df = df.copy()
    df["date"] = pd.to_datetime(df["date"])

    rebalance_dates = get_rebalance_dates(df)
    reb_df = df[df["date"].isin(rebalance_dates)].copy()
    
    if reb_df.empty:
        return pd.DataFrame()

    # 全市場等權重
    reb_df["weight"] = 1.0 / reb_df.groupby("date")["ticker"].transform("count")
    reb_df["rebalance_date"] = reb_df["date"]

    valid_cols = [c for c in ["rebalance_date", "date", "ticker", "close", "weight"] if c in reb_df.columns]
    return reb_df[valid_cols].reset_index(drop=True)

def get_target_weights(portfolio):
    """將投資組合明細轉為目標權重矩陣 (Rebalance Date x Ticker)"""
    if portfolio.empty:
        return pd.DataFrame()

    return portfolio.pivot_table(
        index="rebalance_date",
        columns="ticker",
        values="weight",
        aggfunc="sum",
        fill_value=0.0
    ).sort_index()