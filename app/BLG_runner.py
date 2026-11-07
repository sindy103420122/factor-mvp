import pandas as pd
from data import get_mock_data
from factors import generate_alpha_signals
from portfolio import generate_weights
from backtest import run_single_period_backtest

def run_pipeline():
    print("🚀 [1/4] 啟動台股因子回測管線...")
    
    # 1. Data: 取得計算日資料
    print("📊 [2/4] 載入 Point-in-Time 截面資料...")
    df = get_mock_data(date="2026-11-05")
    
    # 2. Factors: 計算因子與訊號
    print("🧮 [3/4] 計算 US-332, US-496, US-578 因子特徵...")
    signals = generate_alpha_signals(df)
    
    # 3. Portfolio: 計算 Z-score 並分配權重
    print("⚖️  [4/4] 計算 Z-score 並產出投資組合權重...")
    weights = generate_weights(signals, top_n=2)
    
    # 4. Backtest: 模擬次期報酬 (這裡用假資料模擬次期收盤價)
    prices_now = df['close_price']
    prices_next = prices_now * 1.05 # 模擬全面上漲 5% 作為驗證
    
    bt_result = run_single_period_backtest(weights, prices_now, prices_next)
    
    # 5. Report: 產出報告
    print("\n" + "="*40)
    print("📈 MVP 回測績效報告 (單期)")
    print("="*40)
    print(f"投資組合權重配置:\n{weights[weights > 0]}")
    print("-" * 40)
    print(f"原始總報酬 (Gross Return): {bt_result['gross_return']:.4%}")
    print(f"交易成本估算 (Trade Cost):   {bt_result['cost']:.4%}")
    print(f"單期淨報酬 (Net Return):   {bt_result['net_return']:.4%}")
    print("="*40)

if __name__ == "__main__":
    run_pipeline()