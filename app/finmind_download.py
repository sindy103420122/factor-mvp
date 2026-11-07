"""備案資料來源：從 FinMind 免費 API 下載資料，轉成 app/data.py 要的標準格式。

用法（在自己的電腦執行，需要網路）：
  python -m app.finmind_download --limit 300     # 先抽 300 檔試跑（約 1 小時內）
  python -m app.finmind_download                 # 全部上市櫃普通股（數小時，可中斷續傳）
  python -m app.runner --data data/processed     # 下載完後直接跑回測

金鑰：到 FinMind 官網免費註冊取得 token，放在環境變數 FINMIND_TOKEN（不要寫進程式或 commit）。
沒有 token 也能跑，但每小時可下載的次數較少。

只使用免費會員可用的資料表：
  股價用 TaiwanStockPrice（未還原），再以除權息（TaiwanStockDividendResult）
  與減資（TaiwanStockCapitalReductionReferencePrice）的參考價，自行計算還原報酬。
  （FinMind 的還原股價 TaiwanStockPriceAdj 需要付費會員，所以不使用。）

與 TEJ 相比的限制（報告中需說明）：
  1. 月營收沒有實際公布日，一律以「次月 10 日」（法定期限）作為可用日，較保守。
  2. 上市日以「下載資料中第一筆股價日期」近似。
  3. 股票分割、面額變更若下載失敗則不調整（會印出警告），這類事件很少。
"""
import argparse
import os
import random
import time
from pathlib import Path

import numpy as np
import pandas as pd

API_URL = "https://api.finmindtrade.com/api/v4/data"


class LevelError(RuntimeError):
    """免費會員無法使用這個資料表或這種查詢方式。"""
OOS_START = pd.Timestamp("2023-01-01")
CACHE = Path("data/finmind_cache")


# ---------------------------------------------------------------- 下載
def fetch(dataset: str, data_id: str = "", start: str = "", end: str = "",
          max_wait_rounds: int = 3) -> pd.DataFrame:
    """呼叫 FinMind API。遇到次數上限會等待後重試；仍失敗就拋出錯誤（已下載的部分會保留）。"""
    import requests

    token = os.environ.get("FINMIND_TOKEN", "")
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    params = {"dataset": dataset, "data_id": data_id, "start_date": start, "end_date": end}
    for attempt in range(max_wait_rounds + 1):
        resp = requests.get(API_URL, params=params, headers=headers, timeout=60)
        body = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else {}
        if resp.status_code == 200 and body.get("status", 200) == 200:
            return pd.DataFrame(body.get("data", []))
        msg = body.get("msg", resp.text[:200])
        if "level" in str(msg).lower():
            raise LevelError(f"免費會員無法使用 {dataset}（{msg}）")
        if resp.status_code == 402 or "limit" in str(msg).lower():
            if attempt < max_wait_rounds:
                print(f"  已達下載次數上限，等待 10 分鐘後重試（{attempt + 1}/{max_wait_rounds}）...")
                time.sleep(600)
                continue
            raise RuntimeError("已達 FinMind 下載次數上限。已下載的資料都保留了，晚點重新執行同一個指令會從中斷處繼續。")
        raise RuntimeError(f"FinMind 回傳錯誤（{resp.status_code}）：{msg}")
    return pd.DataFrame()


def cached_fetch(kind: str, dataset: str, data_id: str, start: str, end: str) -> pd.DataFrame:
    """每檔股票存一個快取檔，中斷後重跑不會重複下載。"""
    path = CACHE / kind / f"{dataset}_{data_id or 'all'}.csv"
    if path.exists():
        return pd.read_csv(path, dtype={"stock_id": str})
    df = fetch(dataset, data_id, start, end)
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)
    return df


# ---------------------------------------------------------------- 轉換（純函式，可測試）
def is_common_stock(stock_id: pd.Series) -> pd.Series:
    """普通股：4 位數字代碼且不以 0 開頭（排除 ETF、特別股、存託憑證、權證）。"""
    s = stock_id.astype(str)
    return s.str.fullmatch(r"[1-9]\d{3}")


def build_listing(prices: pd.DataFrame, delisting: pd.DataFrame, grace_days: int = 30) -> pd.DataFrame:
    """上市日以第一筆股價近似；下市日取下市清單，但排除「轉板」造成的假下市。

    對應 Scenario: 上櫃轉上市不視為下市。
    判斷方式：下市日之後超過 grace_days 天仍有股價，代表股票仍在交易（例如上櫃轉上市）。
    """
    p = prices.copy()
    p["date"] = pd.to_datetime(p["date"])
    span = p.groupby("stock_id")["date"].agg(["min", "max"])
    delist_date = {}
    d = delisting.copy()
    d["date"] = pd.to_datetime(d["date"])
    for _, row in d.sort_values("date").iterrows():
        sid = str(row["stock_id"])
        if sid in span.index and span.loc[sid, "max"] <= row["date"] + pd.Timedelta(days=grace_days):
            delist_date[sid] = row["date"].strftime("%Y-%m-%d")
    return pd.DataFrame({"stock_id": span.index,
                         "list_date": span["min"].dt.strftime("%Y-%m-%d").values,
                         "delist_date": [delist_date.get(s) for s in span.index]})


def build_revenue(raw: pd.DataFrame) -> pd.DataFrame:
    """月營收：營收月份取 revenue_year / revenue_month；可用日一律為次月 10 日。

    對應 Scenario: FinMind 月營收以次月 10 日為可用日。
    FinMind 的 date 欄位是「營收月份的次月 1 日」，不是公告日，所以不使用。
    """
    r = raw.copy()
    period = pd.PeriodIndex.from_fields(year=r["revenue_year"].astype(int),
                                        month=r["revenue_month"].astype(int), freq="M")
    r["month"] = period.astype(str)
    r["publish_date"] = ((period + 1).to_timestamp() + pd.Timedelta(days=9)).date
    r["stock_id"] = r["stock_id"].astype(str)
    return r[["stock_id", "month", "revenue", "publish_date"]]


def collect_events(dividend: pd.DataFrame, reduction: pd.DataFrame,
                   split: pd.DataFrame = None, par: pd.DataFrame = None) -> pd.DataFrame:
    """把除權息、減資、分割、面額變更整理成同一張表：stock_id, date, before, after。

    before = 事件前一個交易日的收盤價，after = 事件當天的參考價。
    """
    frames = []
    if dividend is not None and not dividend.empty:
        frames.append(dividend.rename(columns={"before_price": "before", "after_price": "after"}))
    if reduction is not None and not reduction.empty:
        frames.append(reduction.rename(columns={"ClosingPriceonTheLastTradingDay": "before",
                                                "PostReductionReferencePrice": "after"}))
    if split is not None and not split.empty:
        frames.append(split.rename(columns={"before_price": "before", "after_price": "after"}))
    if par is not None and not par.empty:
        frames.append(par.rename(columns={"before_close": "before", "after_ref_close": "after"}))
    if not frames:
        return pd.DataFrame(columns=["stock_id", "date", "before", "after"])
    ev = pd.concat([f[["stock_id", "date", "before", "after"]] for f in frames], ignore_index=True)
    ev["stock_id"] = ev["stock_id"].astype(str)
    ev["date"] = pd.to_datetime(ev["date"])
    ev[["before", "after"]] = ev[["before", "after"]].apply(pd.to_numeric, errors="coerce")
    return ev[(ev["before"] > 0) & (ev["after"] > 0)]


def build_prices(raw: pd.DataFrame, events: pd.DataFrame = None) -> pd.DataFrame:
    """由未還原股價與事件參考價，計算還原後的股價指數（起點為 100）。

    對應 Scenario: 除息日的報酬以參考價計算。
    一般交易日：報酬 = 今日收盤 ÷ 昨日收盤 − 1
    事件當天：  報酬 = 今日收盤 ÷ 昨日收盤 × (事件前收盤 ÷ 參考價) − 1
    這樣除息、減資造成的股價跳空不會被誤當成漲跌，與付費的還原股價原理相同。
    """
    p = raw.copy()
    p["stock_id"] = p["stock_id"].astype(str)
    p["date"] = pd.to_datetime(p["date"])
    p = p[p["close"] > 0].sort_values(["stock_id", "date"]).reset_index(drop=True)
    p["factor"] = 1.0
    if events is not None and not events.empty:
        # 事件日若不是交易日（例如停止買賣期間），對到其後第一個交易日
        ev = events.sort_values("date")
        for sid, g in ev.groupby("stock_id"):
            idx = p.index[p["stock_id"] == sid]
            if len(idx) == 0:
                continue
            dates = p.loc[idx, "date"].values
            for _, e in g.iterrows():
                pos = np.searchsorted(dates, np.datetime64(e["date"]), side="left")
                if pos < len(idx) and pos > 0:
                    p.loc[idx[pos], "factor"] *= e["before"] / e["after"]
    raw_ret = p.groupby("stock_id")["close"].pct_change()
    ret = (1 + raw_ret) * p["factor"] - 1
    p["ret"] = ret.fillna(0.0)
    p["adj_close"] = 100 * (1 + p["ret"]).groupby(p["stock_id"]).cumprod()
    limit = np.where(p["date"] < pd.Timestamp("2015-06-01"), 0.07, 0.10)
    p["limit_up"] = ret >= (limit - 0.005)
    out = p.rename(columns={"Trading_money": "trade_value"})
    out["adj_close"] = out["adj_close"].round(6)
    out["date"] = out["date"].dt.date
    return out[["stock_id", "date", "adj_close", "trade_value", "limit_up"]]


def fetch_events_by_range(dataset: str, ids: list, start: str, end: str, kind: str,
                          per_stock_fallback: bool = True) -> pd.DataFrame:
    """先嘗試一次抓全市場（快）；免費會員不允許時，改為逐檔抓（慢但可行）。"""
    try:
        df = cached_fetch(kind, dataset, "", start, end)
        return df[df["stock_id"].astype(str).isin(ids)] if not df.empty else df
    except LevelError:
        if not per_stock_fallback:
            raise
        print(f"  {dataset} 無法一次抓全市場，改為逐檔下載...")
        parts = [cached_fetch(kind, dataset, sid, start, end) for sid in ids]
        parts = [x for x in parts if not x.empty]
        return pd.concat(parts, ignore_index=True) if parts else pd.DataFrame()


# ---------------------------------------------------------------- 主流程
def main(argv=None):
    ap = argparse.ArgumentParser(description="從 FinMind 下載台股資料（備案）")
    ap.add_argument("--price-start", default="2014-01-01")
    ap.add_argument("--revenue-start", default="2013-01-01")
    ap.add_argument("--end", default="2022-12-31")
    ap.add_argument("--limit", type=int, default=None, help="只抽樣 N 檔（固定亂數種子，可重現）")
    ap.add_argument("--out", default="data/processed")
    ap.add_argument("--allow-oos", action="store_true", help="第 7 週驗收時才使用")
    args = ap.parse_args(argv)

    if pd.Timestamp(args.end) >= OOS_START and not args.allow_oos:
        raise SystemExit("結束日期進入樣本外（2023-01 起）。現在不需要樣本外資料，第 7 週再加 --allow-oos。")

    print("1/4 下載股票清單與下市櫃清單...")
    info = cached_fetch("meta", "TaiwanStockInfo", "", "", "")
    delisting = cached_fetch("meta", "TaiwanStockDelisting", "", "", "")
    info = info[info["type"].isin(["twse", "tpex"]) & is_common_stock(info["stock_id"])]
    delisting = delisting[is_common_stock(delisting["stock_id"])]
    delisting = delisting[pd.to_datetime(delisting["date"]) >= pd.Timestamp(args.price_start)]
    ids = sorted(set(info["stock_id"].astype(str)) | set(delisting["stock_id"].astype(str)))
    print(f"  上市櫃普通股（含 {args.price_start} 後下市者）共 {len(ids)} 檔")
    if args.limit:
        ids = sorted(random.Random(42).sample(ids, min(args.limit, len(ids))))
        print(f"  抽樣 {len(ids)} 檔（亂數種子 42）")

    print("2/4 下載股價與月營收（可中斷續傳）...")
    prices, revenue = [], []
    for i, sid in enumerate(ids, 1):
        prices.append(cached_fetch("price", "TaiwanStockPrice", sid, args.price_start, args.end))
        revenue.append(cached_fetch("revenue", "TaiwanStockMonthRevenue", sid, args.revenue_start, args.end))
        if i % 25 == 0 or i == len(ids):
            print(f"  {i}/{len(ids)}")

    print("3/4 下載除權息、減資參考價與加權報酬指數...")
    dividend = fetch_events_by_range("TaiwanStockDividendResult", ids, args.price_start, args.end, "dividend")
    reduction = fetch_events_by_range("TaiwanStockCapitalReductionReferencePrice", ids,
                                      args.price_start, args.end, "reduction")
    optional = {}
    for name, ds in [("split", "TaiwanStockSplitPrice"), ("par", "TaiwanStockParValueChange")]:
        try:
            optional[name] = fetch_events_by_range(ds, ids, args.price_start, args.end, name,
                                                   per_stock_fallback=False)
        except Exception as e:   # 這兩類事件很少，下載失敗只警告，不中斷
            print(f"  警告：{ds} 下載失敗，這類事件不做調整（{e}）")
            optional[name] = None
    events = collect_events(dividend, reduction, optional["split"], optional["par"])
    print(f"  共 {len(events)} 筆除權息、減資等事件，用來計算還原報酬")
    try:
        bench = cached_fetch("meta", "TaiwanStockTotalReturnIndex", "TAIEX", args.price_start, args.end)
        bench = bench.rename(columns={"price": "close"})
    except LevelError:
        print("  警告：無法取得加權報酬指數，改用加權指數（不含息），報告中須說明 benchmark 被低估")
        bench = cached_fetch("meta", "TaiwanStockPrice", "TAIEX", args.price_start, args.end)

    print("4/4 轉成標準格式...")
    prices = pd.concat([p for p in prices if not p.empty], ignore_index=True)
    revenue = pd.concat([r for r in revenue if not r.empty], ignore_index=True)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    std_prices = build_prices(prices, events)
    std_prices.to_csv(out / "prices.csv", index=False)
    build_revenue(revenue).to_csv(out / "revenue.csv", index=False)
    build_listing(std_prices, delisting).to_csv(out / "listing.csv", index=False)
    b = bench[["date", "close"]]
    b.to_csv(out / "benchmark.csv", index=False)
    print(f"完成，已輸出到 {out}/。接著執行：python -m app.runner --data {out}")


if __name__ == "__main__":
    main()
