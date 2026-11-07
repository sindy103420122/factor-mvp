import os
import pandas as pd
import matplotlib.pyplot as plt
from data import get_mock_data
from factors import generate_alpha_signals
from portfolio import generate_weights
from backtest import run_single_period_backtest

def run_pipeline():
    print("🚀 [1/4] 啟動台股因子回測管線...")
    
    print("📊 [2/4] 載入 Point-in-Time 截面資料...")
    df = get_mock_data(date="2026-11-05")
    
    print("🧮 [3/4] 計算 US-332, US-496, US-578 因子特徵...")
    signals = generate_alpha_signals(df)
    
    print("⚖️  [4/4] 計算 Z-score 並產出投資組合權重...")
    weights = generate_weights(signals, top_n=2)
    
    prices_now = df['close_price']
    prices_next = prices_now * 1.05
    bt_result = run_single_period_backtest(weights, prices_now, prices_next)
    
    print("\n" + "="*40)
    print("📈 MVP 回測績效報告 (單期)")
    print("="*40)
    print(f"投資組合權重配置:\n{weights[weights > 0]}")
    print("-" * 40)
    print(f"原始總報酬 (Gross Return): {bt_result['gross_return']:.4%}")
    print(f"交易成本估算 (Trade Cost):   {bt_result['cost']:.4%}")
    print(f"單期淨報酬 (Net Return):   {bt_result['net_return']:.4%}")
    print("="*40)

    # ---------------- 新增的圖表生成區塊 ----------------
    print("\n🎨 正在生成視覺化圖表...")
    os.makedirs("docs", exist_ok=True) # 自動建立 docs 資料夾來放圖片

    # 圖表一：因子特徵比較柱狀圖
    plt.style.use("seaborn-v0_8-darkgrid")
    fig, ax = plt.subplots(figsize=(10, 5))
    signals.plot(kind='bar', ax=ax, colormap='viridis', alpha=0.85)
    ax.set_title("Cross-Sectional Factor Values by Ticker", fontsize=14, fontweight="bold")
    ax.set_ylabel("Factor Value")
    ax.set_xlabel("Stock Ticker")
    plt.xticks(rotation=0)
    plt.legend(["Div Yield", "Inst Buy Ratio", "Margin YoY"])
    plt.tight_layout()
    plt.savefig("docs/factor_comparison.png", dpi=300)
    plt.close()

    # 圖表二：投資組合權重圓餅圖
    active_weights = weights[weights > 0]
    plt.figure(figsize=(6, 6))
    plt.pie(active_weights, labels=active_weights.index, autopct='%1.1f%%', 
            startangle=140, colors=['#4C72B0', '#55A868', '#C44E52'],
            wedgeprops={'edgecolor': 'white', 'linewidth': 2})
    plt.title("Target Portfolio Weights", fontsize=14, fontweight="bold")
    plt.tight_layout()
    plt.savefig("docs/portfolio_pie.png", dpi=300)
    plt.close()

    print("✅ 圖表已成功儲存至 docs/ 資料夾 (factor_comparison.png, portfolio_pie.png)！")

if __name__ == "__main__":
    run_pipeline()