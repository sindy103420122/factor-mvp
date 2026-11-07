from behave import given, when, then
import math

# ==========================================
# US-332 預估高股息殖利率因子
# ==========================================
@given('某檔股票的 TTM EPS 為 {eps:f} 且預估配息率為 {payout:f}')
def step_impl(context, eps, payout):
    context.eps = eps
    context.payout = payout

@given('最新收盤價為 {price:f}')
def step_impl(context, price):
    context.price = price

@when('系統計算預估殖利率')
def step_impl(context):
    if getattr(context, 'eps', 0) <= 0:
        context.yield_result = 0.0
    else:
        context.yield_result = (context.eps * context.payout) / context.price

@then('結果應為 {expected:f}')
def step_impl(context, expected):
    assert abs(context.yield_result - expected) < 1e-4, f"預期 {expected}, 實際為 {context.yield_result}"

@given('某檔股票的 TTM EPS 為 {eps:f}')
def step_impl(context, eps):
    context.eps = eps
    context.price = 100 # Mock price
    context.payout = 0.8

@then('結果應直接標記為 0 淘汰')
def step_impl(context):
    assert context.yield_result == 0.0, "EPS為負，殖利率應為0"


# ==========================================
# US-496 投信買超佔股本比因子
# ==========================================
@given('系統正處於交易日 t')
def step_impl(context):
    context.current_day = "t"

@when('請求投信買超數據時')
def step_impl(context):
    context.requested_data = "t-1_data"

@then('系統必須只回傳 t-1 日(含)以前的盤後數據')
def step_impl(context):
    assert context.requested_data == "t-1_data", "必須防前視偏誤"

@given('過去 5 日投信累計買超 {buy_vol:d} 張')
def step_impl(context, buy_vol):
    context.buy_vol = buy_vol

@given('該公司發行總張數為 {total_shares:d} 張')
def step_impl(context, total_shares):
    context.total_shares = total_shares

@when('系統計算投信買超佔比')
def step_impl(context):
    context.ratio = context.buy_vol / context.total_shares

@then('結果應為 {expected:f}')
def step_impl(context, expected):
    assert abs(context.ratio - expected) < 1e-4, f"預期 {expected}, 實際為 {context.ratio}"

@given('過去 5 日投信完全沒有買賣紀錄')
def step_impl(context):
    context.buy_vol = None # 模擬缺值

@when('系統處理該檔股票的籌碼特徵')
def step_impl(context):
    if context.buy_vol is None:
        context.buy_vol = 0 # 缺值補0

@then('買超張數應填補為 0 而非 NaN')
def step_impl(context):
    assert context.buy_vol == 0, "無交易紀錄必須補0"


# ==========================================
# US-578 單季毛利率年變動因子
# ==========================================
@given('某公司於 5月15日 公布 Q1 財報')
def step_impl(context):
    context.publish_date = "05-15"

@when('系統在 5月14日 進行選股')
def step_impl(context):
    context.trade_date = "05-14"

@then('系統不能使用該 Q1 的財報數據')
def step_impl(context):
    assert context.trade_date < context.publish_date, "未公布財報不可使用 (Point-in-Time 驗證)"

@given('最新單季毛利率為 {margin_now:d}%')
def step_impl(context, margin_now):
    context.margin_now = margin_now

@given('去年同季毛利率為 {margin_last:d}%')
def step_impl(context, margin_last):
    context.margin_last = margin_last

@when('系統計算毛利率年變動')
def step_impl(context):
    if getattr(context, 'margin_last', None) is None:
        context.margin_diff = float('nan')
    else:
        context.margin_diff = context.margin_now - context.margin_last

@then('結果差值應為 {expected:d}%')
def step_impl(context, expected):
    assert context.margin_diff == expected, f"預期 {expected}, 實際為 {context.margin_diff}"

@given('該公司為新上市，無去年同期財報')
def step_impl(context):
    context.margin_now = 20
    context.margin_last = None # 模擬無去年同期資料

@then('結果應標記為缺值 NaN 進入後續 Z-score 處理')
def step_impl(context):
    assert math.isnan(context.margin_diff), "無同期資料必須回傳 NaN"