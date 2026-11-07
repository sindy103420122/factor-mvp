import pandas as pd
import numpy as np

def calc_dividend_yield(df: pd.DataFrame) -> pd.Series:
    """
    US-332 預估高股息殖利率因子
    公式：(TTM EPS * 預估配息率) / 最新收盤價
    """
    # 對應 Scenario: 成功計算正常的預估殖利率
    yields = (df['ttm_eps'] * df['payout_ratio']) / df['close_price']
    
    # 對應 Scenario: 異常情境_TTM EPS為負值時直接淘汰
    # 對應 Scenario: 邊界情境_歷史配息率為0時直接淘汰
    yields = yields.where((df['ttm_eps'] > 0) & (df['payout_ratio'] > 0), 0.0)
    
    return yields

def calc_institutional_buy_ratio(df: pd.DataFrame) -> pd.Series:
    """
    US-496 投信買超佔股本比因子
    公式：過去5日投信買超張數 / 發行總張數
    """
    # 對應 Scenario: 異常情境_過去5個交易日無交易紀錄或停牌 (缺值補0)
    buy_vol = df['inst_buy_5d'].fillna(0.0)
    
    # 對應 Scenario: 成功計算過去5個交易日投信買超佔比
    return buy_vol / df['total_shares']

def calc_gross_margin_yoy(df: pd.DataFrame) -> pd.Series:
    """
    US-578 單季毛利率年變動因子
    公式：最新單季毛利率 - 去年同季毛利率
    """
    # 對應 Scenario: 成功計算毛利率年變動
    # 對應 Scenario: 異常情境_新上市櫃導致無去年同期財報 (相減時遇到 NaN 會自然保留為 NaN)
    return df['margin_now'] - df['margin_last']

def generate_alpha_signals(df: pd.DataFrame) -> pd.DataFrame:
    """
    將所有因子整合成一張訊號表，供 Portfolio 模組使用
    """
    signals = pd.DataFrame(index=df.index)
    signals['factor_div_yield'] = calc_dividend_yield(df)
    signals['factor_inst_buy'] = calc_institutional_buy_ratio(df)
    signals['factor_margin_yoy'] = calc_gross_margin_yoy(df)
    
    return signals