"""成交假設與交易成本。對應 requirements/US-104。

時間約定（AC1）：
  訊號日 = 每月最後一個交易日（只用當天以前的資料）
  成交日 = 訊號日的下一個交易日，以還原收盤價成交
  持有期報酬 = 本次成交日收盤 → 下次成交日收盤
"""
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from app.config import CostConfig


def trade_cost(amount: float, side: str, cost: CostConfig) -> float:
    """單筆交易成本（元）。對應 Scenario: 買進只扣手續費／賣出另扣證交稅。"""
    if side == "buy":
        return amount * (cost.fee_rate + cost.slippage)
    if side == "sell":
        return amount * (cost.fee_rate + cost.tax_rate + cost.slippage)
    raise ValueError(f"未知的買賣方向：{side}")


@dataclass
class RebalanceResult:
    weights: dict                 # 成交後權重（不含現金）
    turnover: float               # （買進 + 賣出）÷ 2，以淨值比例表示
    cost_rate: float              # 交易成本占淨值比例
    log: list = field(default_factory=list)   # 無法成交等紀錄


def rebalance(prev: dict, target: dict, cost: CostConfig, limit_up: set = frozenset()) -> RebalanceResult:
    """把持股從 prev 調整到 target（皆為淨值比例）。

    對應 Scenario: 成交日漲停的股票不得新買進。
    無法買進的部分保留為現金，不重新分配給其他股票（較保守，也較容易稽核）。
    規格不確定點：跌停無法賣出尚未處理（MVP 範圍外）。
    """
    log = []
    final = {}
    for s in set(prev) | set(target):
        old, new = prev.get(s, 0.0), target.get(s, 0.0)
        if new > old and s in limit_up:
            log.append({"stock_id": s, "reason": "漲停無法買進"})
            new = old          # 已持有的部分維持，無法加碼
        if new > 0:
            final[s] = new

    buy = sum(max(final.get(s, 0) - prev.get(s, 0), 0) for s in set(prev) | set(final))
    sell = sum(max(prev.get(s, 0) - final.get(s, 0), 0) for s in set(prev) | set(final))
    cost_rate = buy * (cost.fee_rate + cost.slippage) + sell * (cost.fee_rate + cost.tax_rate + cost.slippage)
    return RebalanceResult(final, (buy + sell) / 2, cost_rate, log)


def month_end_dates(trading_days: pd.DatetimeIndex, start: str, end: str) -> list:
    """每月最後一個交易日。"""
    days = trading_days[(trading_days >= pd.Timestamp(start)) & (trading_days <= pd.Timestamp(end))]
    s = pd.Series(days, index=days)
    return list(s.groupby([days.year, days.month]).max())


def run_backtest(signal_fn, wide_prices: pd.DataFrame, cost: CostConfig, start: str, end: str,
                 limit_up: pd.DataFrame = None, benchmark: pd.Series = None):
    """signal_fn(asof) -> {stock_id: 目標權重}。回傳每月紀錄 DataFrame 與交易紀錄 list。"""
    days = wide_prices.index
    signal_days = month_end_dates(days, start, end)
    filled = wide_prices.ffill()   # 下市後價格停在最後一筆，等同於轉成現金（見規格不確定點）

    records, trade_log = [], []
    nav, held = 1.0, {}
    for i, sig_day in enumerate(signal_days[:-1]):
        pos = days.get_loc(sig_day)
        if pos + 1 >= len(days):
            break
        exec_day = days[pos + 1]
        next_exec_pos = days.get_loc(signal_days[i + 1]) + 1
        if next_exec_pos >= len(days):
            break
        next_exec = days[next_exec_pos]

        target = signal_fn(sig_day)
        lu = set()
        if limit_up is not None and exec_day in limit_up.index:
            row = limit_up.loc[exec_day]
            lu = set(row[row.fillna(False).astype(bool)].index)
        res = rebalance(held, target, cost, lu)
        for item in res.log:
            trade_log.append({"exec_date": exec_day.date(), **item})

        nav *= (1 - res.cost_rate)
        # 持有期報酬
        p0, p1 = filled.loc[exec_day], filled.loc[next_exec]
        rets = (p1 / p0 - 1).reindex(list(res.weights)).fillna(0.0)
        invested = sum(res.weights.values())
        port_ret = float(sum(res.weights[s] * rets[s] for s in res.weights))
        nav *= (1 + port_ret)

        # 權重隨價格漂移，作為下一期的調倉前持股
        growth = 1 + port_ret
        held = {s: res.weights[s] * (1 + rets[s]) / growth for s in res.weights}

        bench_ret = np.nan
        if benchmark is not None:
            b = benchmark.ffill()
            bench_ret = float(b.asof(next_exec) / b.asof(exec_day) - 1)
        records.append({"signal_date": sig_day.date(), "exec_date": exec_day.date(),
                        "end_date": next_exec.date(), "n_holdings": len(res.weights),
                        "invested": invested, "turnover": res.turnover, "cost_rate": res.cost_rate,
                        "gross_return": port_ret, "net_return": (1 - res.cost_rate) * (1 + port_ret) - 1,
                        "benchmark_return": bench_ret, "nav": nav})
    return pd.DataFrame(records), trade_log
