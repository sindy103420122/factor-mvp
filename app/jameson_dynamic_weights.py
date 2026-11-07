"""方向 2：歷史 Rank IC 動態因子權重（獨立模組）。"""
from __future__ import annotations

import numpy as np
import pandas as pd


def rank_ic(factor_scores: pd.Series, forward_returns: pd.Series) -> float:
    """計算同一期股票橫斷面的 Spearman Rank IC。"""
    paired = pd.concat([factor_scores.rename('score'), forward_returns.rename('ret')], axis=1).dropna()
    if len(paired) < 3 or paired['score'].nunique() < 2 or paired['ret'].nunique() < 2:
        return float('nan')
    return float(paired['score'].corr(paired['ret'], method='spearman'))


def compute_ic_history(factor_snapshots: dict, realized_returns: dict) -> pd.DataFrame:
    """輸入每月 asof 的因子截面及該月訊號的後續已實現報酬。

    factor_snapshots[asof]：DataFrame(index=stock_id, columns=factor_name)
    realized_returns[asof]：Series(index=stock_id)，對應 asof 訊號的下一持有期報酬。
    回傳每期 IC，注意：此函式不負責判斷報酬何時可得，請使用
    dynamic_weights(..., availability_dates=...) 保證時點正確。
    """
    rows = []
    for asof, factors in factor_snapshots.items():
        if asof not in realized_returns:
            continue
        rows.append({'signal_date': pd.Timestamp(asof), **{
            factor: rank_ic(factors[factor], realized_returns[asof]) for factor in factors.columns
        }})
    if not rows:
        return pd.DataFrame(index=pd.DatetimeIndex([], name='signal_date'))
    return pd.DataFrame(rows).set_index('signal_date').sort_index()


def dynamic_weights(ic_history: pd.DataFrame, decision_date: str, *,
                    availability_dates: pd.Series, lookback: int = 36,
                    min_periods: int = 36, shrinkage: float = 0.0) -> dict[str, float]:
    """用決策日之前已可得的最近 lookback 期 IC 估計因子權重。

    availability_dates：index=signal_date，value=該期後續報酬實際可得日期。
    禁止用 signal_date 直接代替 availability_date，避免未來資訊洩漏。
    shrinkage=0 為純 IC 加權；0.5 為 IC/等權各半。
    資料不足或全部非正 IC 時退回等權；不使用樣本外資訊調參。
    """
    if lookback < 1 or min_periods < 1 or min_periods > lookback:
        raise ValueError('lookback/min_periods 不合法')
    if not 0 <= shrinkage <= 1:
        raise ValueError('shrinkage 必須在 0 到 1 之間')
    if ic_history.empty or len(ic_history.columns) == 0:
        raise ValueError('至少需要一個因子欄位')
    if ic_history.index.has_duplicates or availability_dates.index.has_duplicates:
        raise ValueError('signal_date 不得重複')
    cols = list(ic_history.columns)
    equal = pd.Series(1.0 / len(cols), index=cols)
    decision = pd.Timestamp(decision_date)
    avail = pd.to_datetime(availability_dates.reindex(ic_history.index))
    eligible = ic_history.loc[(ic_history.index < decision) & (avail < decision)]
    eligible = eligible.sort_index().tail(lookback)
    if len(eligible) < min_periods:
        return equal.to_dict()
    # 各因子須有足夠的有效 IC，不能讓少數樣本因子取得不公平優勢。
    counts = eligible.notna().sum()
    mean_ic = eligible.mean().where(counts >= min_periods, 0.0).fillna(0.0)
    positive = mean_ic.clip(lower=0.0)
    ic_w = positive / positive.sum() if positive.sum() > 0 else equal
    final = (1 - shrinkage) * ic_w + shrinkage * equal
    return final.to_dict()
