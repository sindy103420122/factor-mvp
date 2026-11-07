import os
import pandas as pd
import numpy as np

# 匯入管線中的各個模組
from app.data import prepare_fundamentals, merge_point_in_time
from app.factors import build_factors
from app.signals import generate_signals
from app.portfolio import build_portfolio
from app.backtest import BacktestEngine, calculate_performance

def run_pipeline():
    print("🚀 [1/5] 載入資料與時點對齊 (Point-in-Time)...")
    # 實務上這裡會讀取你的 CSV 檔案
    # prices = pd.read_csv("data/prices.csv", parse_dates=["date"])
    # fundamentals = pd.read_csv("data/fundamentals.csv", parse_dates=["period_end", "published_at"])
    # df = prepare_fundamentals(fundamentals)
    # df = merge_point_in_time(prices, df)
    
    # 這裡建立一個簡單的假資料 DataFrame 確保程式能空轉測試
    dates = pd.date_range("2023-01-01", "2026-09-30", freq="B")
    df = pd.DataFrame({"date": dates, "ticker": "2330", "close": 500, "eps_ttm": 30, "dividend_rate": 0.5, "trust_net_buy": 100, "shares_outstanding": 25930000, "gross_margin_yoy_diff": 0.02})
    
    print("📊 [2/5] 計算因子與橫斷面 Z-score...")
    df = build_factors(df)

    print("🎯 [3/5] 生成多因子合成分數與股票排名...")
    # 預設呼叫 generate_signals，將缺值補 0 並產生 signal_score
    df = generate_signals(df)

    print("💼 [4/5] 建構月調倉等權重投資組合...")
    # 每月底選出 Top 20 檔股票，等權重配置
    portfolio = build_portfolio(df, top_n=20)

    print("📈 [5/5] 執行歷史回測與交易成本核算...")
    # 扣除買賣手續費 0.1425% 與證交稅 0.3%
    engine = BacktestEngine(initial_capital=1_000_000)
    
    # 若 portfolio 有內容則執行回測，否則略過避免報錯
    if not portfolio.empty:
        backtest_result = engine.run(df, portfolio)
        stats = calculate_performance(backtest_result)
        
        print("\n" + "=" * 40)
        print("🏆 【台股智慧因子策略 - 樣本外績效報告】")
        print("=" * 40)
        for k, v in stats.items():
            if "Return" in k or "Volatility" in k or "Drawdown" in k:
                print(f" - {k:<18}: {v:>8.2%}")
            else:
                print(f" - {k:<18}: {v:>8.2f}")
        print("=" * 40 + "\n")
        return backtest_result, stats
    else:
        print("\n⚠️ 警告：股票池過濾後無標的，無法產生回測結果。")
        return None, None

if __name__ == "__main__":
    run_pipeline()