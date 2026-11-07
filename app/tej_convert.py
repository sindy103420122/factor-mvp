"""把 TEJ 匯出的原始檔，轉成 app/data.py 要的標準格式。

用法：
  python -m app.tej_convert --raw data/raw --out data/processed

★ 第一次使用前，請先打開你從 TEJ 匯出的 CSV，對照下方 COLUMN_MAP 的「右邊」改成實際欄位名稱。
  下方欄位名稱是常見寫法的「範例」，不同資料表、不同匯出方式的名稱可能不同，以實際檔案為準。
★ 原始檔（data/raw/）有授權限制，不可 commit 到 GitHub（.gitignore 已排除）。
"""
import argparse
from pathlib import Path

import numpy as np
import pandas as pd

# ---- 1. 欄位對照：左邊是系統標準名稱，右邊請改成你的 TEJ 匯出欄位名稱 ----
COLUMN_MAP = {
    "prices": {   # 日股價檔
        "stock_id": "證券代碼",
        "date": "年月日",
        "adj_close": "收盤價(元)",        # 必須是「調整後」股價表的收盤價
        "raw_close": "未調整收盤價(元)",  # 用來判斷漲停；沒有就留空字串 ""
        "trade_value": "成交金額(千元)",
    },
    "revenue": {  # 月營收檔
        "stock_id": "證券代碼",
        "month": "年月",
        "revenue": "單月營收(千元)",
        "publish_date": "營收發布日",       # 沒有這欄就留空字串 ""，會改用保守期限
    },
    "listing": {  # 上下市資料
        "stock_id": "證券代碼",
        "list_date": "上市日",
        "delist_date": "下市日",
    },
    "benchmark": {  # 加權報酬指數（含息）
        "date": "年月日",
        "close": "收盤價(元)",
    },
}

# ---- 2. 單位：TEJ 金額常以「千元」計，要乘回元，否則流動性門檻會差 1000 倍 ----
TRADE_VALUE_MULTIPLIER = 1000
REVENUE_MULTIPLIER = 1000

FILES = {"prices": "prices_raw.csv", "revenue": "revenue_raw.csv",
         "listing": "listing_raw.csv", "benchmark": "benchmark_raw.csv"}


def parse_date(s: pd.Series) -> pd.Series:
    """日期可能是 20150508、20150508.0（數字欄有空值時）、2015/05/08 或 2015-05-08。"""
    num = pd.to_numeric(s, errors="coerce")
    as_text = s.astype(str).where(num.isna(), num.astype("Int64").astype(str))
    return pd.to_datetime(as_text.str.replace("/", "-"), errors="coerce", format="mixed")


def clean_stock_id(s: pd.Series) -> pd.Series:
    """TEJ 常把代碼與名稱放在同一欄（例：'2330 台積電'），只保留代碼。"""
    return s.astype(str).str.strip().str.split().str[0]


def _read(raw: Path, key: str) -> pd.DataFrame:
    df = pd.read_csv(raw / FILES[key], encoding="utf-8-sig")
    mapping = {v: k for k, v in COLUMN_MAP[key].items() if v}
    missing = [v for v in mapping if v not in df.columns]
    if missing:
        raise KeyError(f"{FILES[key]} 找不到欄位 {missing}，請修改 COLUMN_MAP['{key}']。"
                       f"\n檔案實際欄位：{list(df.columns)}")
    return df.rename(columns=mapping)[list(mapping.values())]


def limit_up_flag(df: pd.DataFrame) -> pd.Series:
    """用未調整收盤價推估是否漲停。

    台股漲跌幅在 2015-06-01 由 7% 放寬為 10%，所以門檻依日期不同。
    以「漲幅 >= 漲停幅度 − 0.5%」近似判斷（實際漲停價有跳動單位進位）。
    規格不確定點：TEJ 若有直接的漲跌停欄位，應優先使用該欄位。
    """
    if "raw_close" not in df:
        return pd.Series(False, index=df.index)
    df = df.sort_values(["stock_id", "date"])
    chg = df.groupby("stock_id")["raw_close"].pct_change()
    limit = np.where(df["date"] < pd.Timestamp("2015-06-01"), 0.07, 0.10)
    return (chg >= limit - 0.005).reindex(df.index)


def conservative_publish_date(month: pd.Series) -> pd.Series:
    """沒有實際公布日時，以法定期限「次月 10 日」作為最早可用日（保守替代）。"""
    return (pd.PeriodIndex(month, freq="M") + 1).to_timestamp() + pd.Timedelta(days=9)


def convert(raw_dir: str, out_dir: str) -> None:
    raw, out = Path(raw_dir), Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    p = _read(raw, "prices")
    p["stock_id"] = clean_stock_id(p["stock_id"])
    p["date"] = parse_date(p["date"])
    p["trade_value"] = pd.to_numeric(p["trade_value"], errors="coerce") * TRADE_VALUE_MULTIPLIER
    p["limit_up"] = limit_up_flag(p)
    p[["stock_id", "date", "adj_close", "trade_value", "limit_up"]].to_csv(out / "prices.csv", index=False)

    r = _read(raw, "revenue")
    r["stock_id"] = clean_stock_id(r["stock_id"])
    r["month"] = pd.to_datetime(r["month"].astype(str).str.replace("/", "-")).dt.strftime("%Y-%m")
    r["revenue"] = pd.to_numeric(r["revenue"], errors="coerce") * REVENUE_MULTIPLIER
    if "publish_date" in r:
        r["publish_date"] = parse_date(r["publish_date"])
        fallback = conservative_publish_date(r["month"])
        n_missing = r["publish_date"].isna().sum()
        r["publish_date"] = r["publish_date"].fillna(pd.Series(fallback, index=r.index))
    else:
        n_missing = len(r)
        r["publish_date"] = conservative_publish_date(r["month"])
    print(f"月營收：{len(r)} 筆，其中 {n_missing} 筆缺公布日，已用次月 10 日替代")
    r["publish_date"] = pd.to_datetime(r["publish_date"]).dt.date
    r[["stock_id", "month", "revenue", "publish_date"]].to_csv(out / "revenue.csv", index=False)

    lst = _read(raw, "listing")
    lst["stock_id"] = clean_stock_id(lst["stock_id"])
    lst["list_date"] = parse_date(lst["list_date"]).dt.date
    lst["delist_date"] = parse_date(lst["delist_date"]).dt.date
    lst.to_csv(out / "listing.csv", index=False)

    b = _read(raw, "benchmark")
    b["date"] = parse_date(b["date"])
    b.to_csv(out / "benchmark.csv", index=False)
    print(f"已輸出到 {out}/")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw", default="data/raw")
    ap.add_argument("--out", default="data/processed")
    a = ap.parse_args()
    convert(a.raw, a.out)
