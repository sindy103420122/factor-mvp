import pandas as pd

def run_single_period_backtest(weights: pd.Series, prices_now: pd.Series, prices_next: pd.Series) -> dict:
    """
    執行單期回測，計算報酬率並扣除台股標準交易成本。
    """
    # 台股交易成本估算：
    # 買進：手續費 0.1425%
    # 賣出：手續費 0.1425% + 證交稅 0.3%
    # 單趟完整進出總成本率約為 0.00585 (0.585%)
    trade_cost_rate = 0.00585 
    
    # 1. 計算各檔股票的期報酬率
    stock_returns = (prices_next - prices_now) / prices_now
    
    # 2. 投資組合原始總報酬 (權重 * 個股報酬)
    gross_return = (weights * stock_returns).sum()
    
    # 3. 估算交易成本 (MVP 假設每期皆為全倉換股的極端保守估算)
    turnover = weights.sum() # 建倉部位總和
    cost = turnover * trade_cost_rate
    
    # 4. 淨報酬率
    net_return = gross_return - cost
    
    return {
        "gross_return": gross_return,
        "net_return": net_return,
        "turnover": turnover,
        "cost": cost
    }