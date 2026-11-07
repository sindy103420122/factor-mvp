"""US-103 的步驟定義。對應 features/universe.feature。"""
import pandas as pd
from behave import given, when, then

from app.universe import build_universe


def _num(text):
    return float(text.replace(",", ""))


@given('流動性門檻為過去 60 日平均成交金額 {amount} 元')
def step_threshold(context, amount):
    context.min_value = _num(amount)
    context.adv, context.delist = {}, {}


@given('股票 "{stock}" 過去 60 日平均成交金額為 {amount} 元')
def step_adv(context, stock, amount):
    context.adv[stock] = _num(amount)


@given('股票 "{stock}" 於 "{date}" 下市')
def step_delist(context, stock, date):
    context.delist[stock] = date


@when('系統在 "{asof}" 建立股票池')
def step_build(context, asof):
    days = pd.bdate_range(end=asof, periods=60)
    trade_value = pd.DataFrame({s: [v] * 60 for s, v in context.adv.items()}, index=days)
    listing = pd.DataFrame({"stock_id": list(context.adv), "list_date": "2000-01-01",
                            "delist_date": [context.delist.get(s) for s in context.adv]})
    context.universe = build_universe(trade_value, listing, asof, context.min_value, 60)


@then('股票 "{stock}" 在股票池中')
def step_in(context, stock):
    assert stock in context.universe, context.universe


@then('股票 "{stock}" 不在股票池中')
def step_not_in(context, stock):
    assert stock not in context.universe, context.universe
