"""綜合分數與選股。對應 requirements/US-104 的 baseline 選股規則。

方向 2（智慧調權重）的接口：combine_scores 的 weights 參數。
baseline 傳入固定等權；智慧方法只需要產生「每期不同的 weights」，其餘流程不變。
"""
import pandas as pd

from app.factors import cross_section_zscore


def combine_scores(factor_values: pd.DataFrame, weights: dict) -> pd.Series:
    """factor_values：index=stock_id，每欄一個因子（原始值，方向已調整為越大越好）。

    每個因子先在橫斷面做 z-score，再依 weights 加權平均。
    規格不確定點：任一因子缺值的股票，目前直接排除（不以其他因子代替）。
    """
    z = factor_values.apply(cross_section_zscore)
    z = z.dropna(how="any")
    w = pd.Series(weights).reindex(z.columns).fillna(0.0)
    if w.sum() == 0:
        raise ValueError("因子權重總和為 0")
    return (z * w).sum(axis=1) / w.sum()


def select_top_n(score: pd.Series, n: int) -> dict:
    """依分數取前 N 檔、等權。分數相同時以股票代號排序，確保可重現。"""
    if score.empty:
        return {}
    # 先依代號排序，再穩定排序分數，讓同分時結果固定
    ranked = score.sort_index().sort_values(ascending=False, kind="mergesort")
    picks = list(ranked.index[:n])
    return {s: 1.0 / len(picks) for s in picks}
