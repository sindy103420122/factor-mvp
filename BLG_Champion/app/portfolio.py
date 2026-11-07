import pandas as pd

def calculate_z_scores(signals: pd.DataFrame) -> pd.DataFrame:
    """
    將所有因子進行 Z-score 標準化。
    對於缺值 (NaN)，採用中位數填補，以確保不會因單一因子缺漏而整筆失效。
    """
    filled_signals = signals.fillna(signals.median())
    # Z-score 公式：(X - Mean) / Std
    return (filled_signals - filled_signals.mean()) / filled_signals.std(ddof=0)

def generate_weights(signals: pd.DataFrame, top_n: int = 2) -> pd.Series:
    """
    將因子訊號轉化為投資組合權重。
    使用 Z-score 等權重相加，選出總分最高的前 N 檔股票「等權重買進」。
    """
    # 1. 取得 Z-score
    z_scores = calculate_z_scores(signals)
    
    # 2. 多因子等權重相加 (US-332 + US-496 + US-578)
    total_score = z_scores.sum(axis=1)
    
    # 3. 挑選總分最高的前 N 檔股票 (MVP 預設挑 2 檔)
    top_stocks = total_score.nlargest(top_n).index
    
    # 4. 分配資金權重
    weights = pd.Series(0.0, index=signals.index)
    weights[top_stocks] = 1.0 / top_n # 等權重分配 (例如 2 檔就是各 50%)
    
    return weights