"""備案資料轉換的步驟定義。對應 features/finmind_data.feature。不需要網路。"""
import pandas as pd
from behave import given, when, then

from app.finmind_download import build_listing, build_revenue, is_common_stock


@given('FinMind 回傳股票 "{stock}" 在 {year:d} 年 {month:d} 月的營收 {revenue:d}')
def step_fm_revenue(context, stock, year, month, revenue):
    # FinMind 的 date 是營收月份的次月 1 日，刻意放進來，確認程式不會誤用它
    context.fm_revenue = pd.DataFrame([{"date": f"{year}-{month + 1:02d}-01", "stock_id": stock,
                                        "revenue": revenue, "revenue_year": year, "revenue_month": month}])


@when('系統轉換 FinMind 月營收')
def step_convert_revenue(context):
    context.std_revenue = build_revenue(context.fm_revenue)


@then('股票 "{stock}" 營收月份 "{month}" 的可用日為 "{date}"')
def step_revenue_date(context, stock, month, date):
    row = context.std_revenue[(context.std_revenue["stock_id"] == stock) &
                              (context.std_revenue["month"] == month)].iloc[0]
    assert str(row["publish_date"]) == date, row["publish_date"]


@given('股票 "{stock}" 的股價資料從 "{start}" 到 "{end}"')
def step_price_span(context, stock, start, end):
    if not hasattr(context, "span_prices"):
        context.span_prices, context.delist_rows = [], []
    context.span_prices += [{"stock_id": stock, "date": d} for d in (start, end)]


@given('下市櫃清單記錄股票 "{stock}" 於 "{date}" 下櫃')
def step_delist_record(context, stock, date):
    context.delist_rows.append({"stock_id": stock, "date": date})


@when('系統建立上下市資料')
def step_build_listing(context):
    context.listing = build_listing(pd.DataFrame(context.span_prices),
                                    pd.DataFrame(context.delist_rows)).set_index("stock_id")


@then('股票 "{stock}" 沒有下市日')
def step_no_delist(context, stock):
    assert pd.isna(context.listing.loc[stock, "delist_date"])


@then('股票 "{stock}" 的下市日為 "{date}"')
def step_delist_date(context, stock, date):
    assert str(context.listing.loc[stock, "delist_date"]) == date


@given('代碼清單 "{codes}"')
def step_codes(context, codes):
    context.codes = pd.Series([c.strip() for c in codes.split(",")])


@when('系統篩選普通股')
def step_filter(context):
    context.kept = sorted(context.codes[is_common_stock(context.codes)])


@then('保留的代碼為 "{codes}"')
def step_kept(context, codes):
    assert context.kept == [c.strip() for c in codes.split(",")], context.kept


# ---- 還原報酬（除權息、減資）----
from app.finmind_download import build_prices, collect_events  # noqa: E402


@given('股票 "{stock}" 的未還原收盤價為 "{d1}" {p1:g} 元、"{d2}" {p2:g} 元')
def step_raw_prices(context, stock, d1, p1, d2, p2):
    context.raw_prices = pd.DataFrame([
        {"stock_id": stock, "date": d1, "close": p1, "Trading_money": 1e8},
        {"stock_id": stock, "date": d2, "close": p2, "Trading_money": 1e8}])
    context.dividend_rows, context.reduction_rows = [], []


@given('股票 "{stock}" 於 "{date}" 除息，除息前收盤 {before:g} 元、參考價 {after:g} 元')
def step_dividend(context, stock, date, before, after):
    context.dividend_rows.append({"stock_id": stock, "date": date,
                                  "before_price": before, "after_price": after})


@given('股票 "{stock}" 於 "{date}" 減資恢復買賣，停止買賣前收盤 {before:g} 元、參考價 {after:g} 元')
def step_reduction(context, stock, date, before, after):
    context.reduction_rows.append({"stock_id": stock, "date": date,
                                   "ClosingPriceonTheLastTradingDay": before,
                                   "PostReductionReferencePrice": after})


@when('系統計算還原報酬')
def step_adjust(context):
    events = collect_events(pd.DataFrame(context.dividend_rows), pd.DataFrame(context.reduction_rows))
    context.adj = build_prices(context.raw_prices, events)


@then('股票 "{stock}" 在 "{date}" 的報酬約為 {pct:g}%')
def step_adj_return(context, stock, date, pct):
    a = context.adj[context.adj["stock_id"] == stock].set_index("date")["adj_close"]
    a.index = a.index.astype(str)
    ret = a[date] / a.shift(1)[date] - 1
    assert abs(ret - pct / 100) < 0.0001, ret
