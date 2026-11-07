"""US-104 的步驟定義。對應 features/backtest_cost.feature。"""
import re

from behave import given, when, then

from app.backtest import rebalance, trade_cost
from app.config import CostConfig, OutOfSampleLockedError, Settings, check_period

NAV = 1_000_000  # 以 100 萬元淨值換算成本金額


def _holdings(text):
    """把 '"A" 50%、"B" 50%' 轉成 {"A": 0.5, "B": 0.5}。"""
    return {s: float(p) / 100 for s, p in re.findall(r'"(\w+)" (\d+(?:\.\d+)?)%', text)}


@given('手續費率 {fee:g}%，證交稅率 {tax:g}%，滑價率 {slip:g}%')
def step_cost(context, fee, tax, slip):
    context.cost = CostConfig(fee / 100, tax / 100, slip / 100)
    context.limit_up = set()


@when('回測引擎買進 {amount} 元股票')
def step_buy(context, amount):
    context.trade_cost = trade_cost(float(amount.replace(",", "")), "buy", context.cost)


@when('回測引擎賣出 {amount} 元股票')
def step_sell(context, amount):
    context.trade_cost = trade_cost(float(amount.replace(",", "")), "sell", context.cost)


@then('該筆交易成本為 {amount} 元')
def step_check_cost(context, amount):
    assert abs(context.trade_cost - float(amount.replace(",", ""))) < 1e-6, context.trade_cost


@given('調倉前持有 {text}')
def step_prev(context, text):
    context.prev = _holdings(text)


@given('股票 "{stock}" 在成交日漲停')
def step_limit_up(context, stock):
    context.limit_up.add(stock)


@when('調倉目標為 {text}')
def step_target(context, text):
    context.res = rebalance(context.prev, _holdings(text), context.cost, context.limit_up)


@then('本期換手率為 {pct:g}%')
def step_turnover(context, pct):
    assert abs(context.res.turnover - pct / 100) < 1e-9, context.res.turnover


@then('本期交易成本為 {amount:d} 元')
def step_period_cost(context, amount):
    assert abs(context.res.cost_rate * NAV - amount) < 1e-6


@then('股票 "{stock}" 的成交後權重為 {pct:g}%')
def step_weight(context, stock, pct):
    assert abs(context.res.weights.get(stock, 0.0) - pct / 100) < 1e-9


@then('股票 "{stock}" 被記錄為 "{reason}"')
def step_logged(context, stock, reason):
    assert {"stock_id": stock, "reason": reason} in context.res.log, context.res.log


@given('樣本外期間從 "{start}" 開始且尚未解鎖')
def step_oos(context, start):
    context.settings = Settings(oos_start=start, unlock_oos=False)


@when('研究員要求回測到 "{end}"')
def step_request(context, end):
    try:
        check_period(end, context.settings)
        context.error = None
    except OutOfSampleLockedError as e:
        context.error = e


@then('系統拒絕執行並提示樣本外尚未解鎖')
def step_refused(context):
    assert context.error is not None and "尚未解鎖" in str(context.error)
