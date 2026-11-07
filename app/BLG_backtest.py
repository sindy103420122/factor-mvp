import numpy as np
import pandas as pd

class BacktestEngine:
    def __init__(
        self,
        initial_capital=1_000_000,
        commission=0.001425,
        transaction_tax=0.003,
        slippage=0.001  # 加入 0.1% 滑價預設值，符合專案真實交易成本規範
    ):
        self.initial_capital = float(initial_capital)
        self.commission = commission
        self.transaction_tax = transaction_tax
        self.slippage = slippage

    def run(self, prices, portfolio):
        """極速精簡版月調倉回測引擎 (NumPy 矩陣運算)"""
        if portfolio.empty:
            raise ValueError("投資組合 (Portfolio) 不能為空。")

        # 1. 整理報酬率與目標權重矩陣
        prices = prices.copy().sort_values(["ticker", "date"])
        prices["daily_return"] = prices.groupby("ticker")["close"].pct_change()

        returns = prices.pivot(index="date", columns="ticker", values="daily_return").fillna(0.0)
        targets = portfolio.pivot_table(index="rebalance_date", columns="ticker", values="weight", aggfunc="sum", fill_value=0.0)

        # 2. 一次性對齊日期與標的
        all_dates = returns.index.union(targets.index).sort_values()
        all_tickers = returns.columns.union(targets.columns)

        returns = returns.reindex(index=all_dates, columns=all_tickers, fill_value=0.0)
        targets = targets.reindex(index=all_dates, columns=all_tickers, fill_value=0.0)

        ret_mat, target_mat = returns.values, targets.values
        rebalance_mask = (targets.sum(axis=1) > 0).values

        current_w = np.zeros(len(all_tickers))
        nav = self.initial_capital
        history = []

        # 3. 核心向量化迴圈
        for t in range(len(all_dates)):
            day_ret = ret_mat[t]
            gross_ret = float(np.sum(current_w * day_ret))

            # 權重隨市場價格漂移
            updated_w = current_w * (1.0 + day_ret)
            total_val = np.sum(updated_w)
            updated_w = updated_w / total_val if total_val > 0 else np.zeros_like(updated_w)

            total_cost, buy_turnover, sell_turnover = 0.0, 0.0, 0.0

            # 遇到調倉日扣除手續費、證交稅與滑價
            if rebalance_mask[t]:
                target_w = target_mat[t]
                change = target_w - updated_w
                buy_turnover = float(np.sum(np.maximum(change, 0)))
                sell_turnover = float(np.sum(np.maximum(-change, 0)))

                # 買賣皆須承受滑價與手續費，賣出額外扣證交稅
                execution_cost = self.commission + self.slippage
                total_cost = (buy_turnover + sell_turnover) * execution_cost + sell_turnover * self.transaction_tax
                current_w = target_w.copy()
            else:
                current_w = updated_w.copy()

            prev_nav = history[-1]["nav"] if history else self.initial_capital
            nav = nav * (1.0 + gross_ret) * (1.0 - total_cost)

            history.append({
                "date": all_dates[t],
                "nav": nav,
                "net_return": (nav / prev_nav) - 1.0 if prev_nav > 0 else 0.0,
                "turnover": buy_turnover + sell_turnover,
                "total_cost": total_cost
            })

        return pd.DataFrame(history).set_index("date")


def calculate_performance(backtest):
    """計算基本績效與風險統計指標"""
    if backtest.empty or "nav" not in backtest.columns or len(backtest) < 2:
        return {}

    nav, returns = backtest["nav"], backtest["net_return"]
    total_ret = (nav.iloc[-1] / nav.iloc[0]) - 1.0
    days = max(len(nav) - 1, 1)

    # 確保不會發生負數開次方的複數崩潰錯誤
    ann_ret = ((nav.iloc[-1] / nav.iloc[0]) ** (252.0 / days)) - 1.0 if nav.iloc[-1] > 0 else -1.0
    ann_vol = float(returns.std() * np.sqrt(252))
    sharpe = ann_ret / ann_vol if ann_vol > 0 else np.nan
    mdd = float(((nav / nav.cummax()) - 1.0).min())
    avg_turnover = backtest["turnover"].mean() * 252 / 12  # 估算月均換手率

    return {
        "Total Return": total_ret,
        "Annual Return": ann_ret,
        "Annual Volatility": ann_vol,
        "Sharpe Ratio": sharpe,
        "Max Drawdown": mdd,
        "Avg Monthly Turnover": avg_turnover
    }
