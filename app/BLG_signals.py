import numpy as np
import pandas as pd

# 預設對應專題要求的 5 大因子 Z-score 欄位
DEFAULT_WEIGHTS = {
    "z_est_dividend_yield": 0.20,      # 預估高股息殖利率 (US-332)
    "z_itc_net_buy_ratio": 0.20,       # 投信買超佔股本比 (US-496)
    "z_gross_margin_yoy_diff": 0.20,   # 單季毛利率年變動 (US-578)
    "z_earnings_quality": 0.20,        # 盈餘品質
    "z_low_volatility": 0.20           # 低波動
}

def generate_signals(df, weights=None, min_factors=3):
    """
    計算多因子合成分數 (Signal Score) 與每日橫斷面排名 (Signal Rank)
    """
    df = df.copy()
    weights = weights or DEFAULT_WEIGHTS

    # 1. 權重檢查與正規化
    weight_s = pd.Series(weights)
    if (weight_s < 0).any() or weight_s.sum() <= 0:
        raise ValueError("權重必須為非負數且總和需大於 0。")

    # 若資料欄位缺少某個預設因子，則拋出明確錯誤
    missing_cols = set(weight_s.index) - set(df.columns)
    if missing_cols:
        raise ValueError(f"缺少因子欄位: {missing_cols}")

    norm_weights = weight_s / weight_s.sum()
    factor_cols = list(norm_weights.index)

    # 2. 合成分數計算 (向量化運算)
    # 缺值因子補 0 (Z-score 0 代表中性/市場平均)，避免單一因子缺失導致淘汰
    valid_count = df[factor_cols].notna().sum(axis=1)
    weighted_score = df[factor_cols].fillna(0).mul(norm_weights).sum(axis=1)

    # 只有當有效因子數量 >= min_factors 時才保留分數，否則淘汰 (NaN)
    df["signal_score"] = np.where(valid_count >= min_factors, weighted_score, np.nan)

    # 3. 每日橫斷面排名 (1 代表最優股票)
    # 使用 method="min"，確保同分股票排名相同，避免隨機偏誤
    df["signal_rank"] = (
        df.groupby("date")["signal_score"]
        .rank(ascending=False, method="min")
    )

    return df
