"""US-102 的步驟定義。對應 features/momentum.feature。"""
import math

import pandas as pd
from behave import given, when, then

from app.factors import momentum_12_1, to_wide_prices


@given('股票 "{stock}" 的還原收盤價如下')
def step_prices(context, stock):
    if not hasattr(context, "price_rows"):
        context.price_rows = []
    context.price_rows += [{"stock_id": stock, "date": r["date"], "adj_close": float(r["adj_close"])}
                           for r in context.table]


@given('股票 "{stock}" 在 "{date}" 的還原收盤價為 {price:d}')
def step_future_price(context, stock, date, price):
    context.price_rows.append({"stock_id": stock, "date": date, "adj_close": float(price)})


@when('系統在 "{asof}" 計算動能因子')
def step_mom(context, asof):
    context.mom = momentum_12_1(to_wide_prices(pd.DataFrame(context.price_rows)), asof)


@then('股票 "{stock}" 的動能為 {pct:d}%')
def step_mom_value(context, stock, pct):
    assert abs(context.mom[stock] - pct / 100) < 1e-9, context.mom[stock]


@then('股票 "{stock}" 的動能為缺值')
def step_mom_nan(context, stock):
    assert math.isnan(context.mom[stock])
