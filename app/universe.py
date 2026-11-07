"""可交易股票池。對應 requirements/US-103。"""
import pandas as pd


def build_universe(trade_value: pd.DataFrame, listing: pd.DataFrame, asof: str,
                   min_avg_value: float, lookback: int = 60) -> list:
    """回傳 asof 當天可入選的股票代號清單。

    trade_value：index=date, columns=stock_id 的每日成交金額（元）
    listing：stock_id, list_date, delist_date（未下市為空值）
    """
    asof_ts = pd.Timestamp(asof)
    # AC2：平均成交金額只用 asof 當天以前的資料
    recent = trade_value.loc[:asof_ts].tail(lookback)
    avg_value = recent.mean()
    liquid = set(avg_value[avg_value >= min_avg_value].index)  # 對應 Scenario: 流動性不足的股票被排除

    lst = listing.copy()
    lst["list_date"] = pd.to_datetime(lst["list_date"])
    lst["delist_date"] = pd.to_datetime(lst["delist_date"])
    # 對應 Scenario: 已下市的股票不得入選；日後才下市的股票在下市前仍可入選
    # 只看「asof 當時」的狀態，不看今天的狀態，避免存活者偏誤
    listed = lst[(lst["list_date"] <= asof_ts) &
                 (lst["delist_date"].isna() | (lst["delist_date"] > asof_ts))]
    tradable = set(listed["stock_id"])

    return sorted(liquid & tradable)
