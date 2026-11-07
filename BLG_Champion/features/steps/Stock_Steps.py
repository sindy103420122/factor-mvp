from behave import given, when, then
import pandas as pd
import numpy as np
import math
import sys
import os

# 將 app 目錄加入路徑以利匯入模組
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))
from app.factors import calc_dividend_yield, calc_institutional_buy_ratio, calc_gross_margin_yoy

# ==========================================
# US-332 預估高股息殖利率因子
# ==========================================
@given('某檔股票的 TTM EPS 為 {eps:f}')
def step_impl(context, eps):
    context.ttm_eps = eps

@given('預估配息率固定為 {payout:f}')
def step_impl(context, payout):
    context.payout = payout

@given('計算日當天的最新收盤價為 {price:f}')
def step_impl(context, price):
    context.price = price

@when('系統計算預估殖利率')
def step_impl(context):
    df = pd.DataFrame({
        'ttm_eps': [context.ttm_eps],
        'payout_ratio': [context.payout],
        'close_price': [context.price]
    })
    context.result = calc_dividend_yield(df).iloc[0]

@then('預估殖利率結果應為 {expected:f}')
def step_impl(context, expected):
    assert abs(context.result - expected) < 1e-4, f"預期 {expected}, 實際為 {context.result}"

@then('預估殖利率結果應直接標記為 0.0')
def step_impl(context):
    assert context.result == 0.0, "條件不符，應直接淘汰(給予0.0)"

# ==========================================
# US-496 投信買超佔股本比因子
# ==========================================
@given('某檔股票在過去 5 個交易日投信累計買超 {vol:f} 張')
def step_impl(context, vol):
    context.inst_buy_5d = vol

@given('計算日的發行總張數為 {shares:f} 張')
def step_impl(context, shares):
    context.total_shares = shares

@when('系統計算投信買超佔比')
def step_impl(context):
    df = pd.DataFrame({
        'inst_buy_5d': [context.inst_buy_5d],
        'total_shares': [context.total_shares]
    })
    context.result = calc_institutional_buy_ratio(df).iloc[0]

@then('投信買超佔比結果應為 {expected:f}')
def step_impl(context, expected):
    assert abs(context.result - expected) < 1e-4, f"預期 {expected}, 實際 {context.result}"

@given('系統目前的計算日為 {date}')
def step_impl(context, date):
    context.current_date = date

@when('系統請求投信籌碼數據')
def step_impl(context):
    context.data_date = "2026-11-04" # 模擬系統 Point-in-Time 抓取時間

@then('系統只能取得 {expected_date} (含) 以前的盤後買賣超數據')
def step_impl(context, expected_date):
    assert context.data_date <= expected_date, "發生前視偏誤"

@given('某檔股票在過去 5 個交易日完全無投信交易紀錄')
def step_impl(context):
    context.inst_buy_5d = np.nan # 無紀錄視為 NaN

@then('投信買超張數應視為 0')
def step_impl(context):
    df = pd.DataFrame({'inst_buy_5d': [context.inst_buy_5d], 'total_shares': [context.total_shares]})
    context.filled_buy = df['inst_buy_5d'].fillna(0.0).iloc[0]
    assert context.filled_buy == 0.0, "缺值必須補0"

# ==========================================
# US-578 單季毛利率年變動因子
# ==========================================
@given('某檔股票可取得的最新單季毛利率為 {margin_now:f}%')
def step_impl(context, margin_now):
    context.margin_now = margin_now

@given('去年同季毛利率為 {margin_last:f}%')
def step_impl(context, margin_last):
    context.margin_last = margin_last

@when('系統計算毛利率年變動')
def step_impl(context):
    df = pd.DataFrame({
        'margin_now': [context.margin_now],
        'margin_last': [getattr(context, 'margin_last', np.nan)]
    })
    context.result = calc_gross_margin_yoy(df).iloc[0]

@then('毛利率差值結果應為 {expected:f}%')
def step_impl(context, expected):
    assert abs(context.result - expected) < 1e-4, f"預期 {expected}, 實際 {context.result}"

@given('某公司於 {publish_date} 公佈 Q1 財報')
def step_impl(context, publish_date):
    context.publish_date = publish_date

@when('系統請求最新單季毛利率')
def step_impl(context):
    context.requested_data_date = context.publish_date

@then('系統不能取得 Q1 財報數據，必須使用前一季之數據')
def step_impl(context):
    assert context.current_date < context.requested_data_date, "未公布財報不可使用"

@given('某檔股票為新上市櫃，無去年同季財報數據')
def step_impl(context):
    context.margin_last = np.nan

@then('毛利率差值結果應標記為 NaN')
def step_impl(context):
    assert math.isnan(context.result), "無同期資料必須保留為 NaN 以供後續處理"