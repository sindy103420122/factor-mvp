"""績效摘要。對應 requirements/US-104 AC5。月頻計算，無風險利率假設為 0。"""
import numpy as np
import pandas as pd


def summarize(monthly: pd.DataFrame) -> dict:
    r = monthly["net_return"]
    b = monthly["benchmark_return"]
    n = len(r)
    if n == 0:
        return {}
    nav = (1 + r).cumprod()
    ann_ret = nav.iloc[-1] ** (12 / n) - 1
    ann_vol = r.std() * np.sqrt(12)
    mdd = (nav / nav.cummax() - 1).min()
    out = {
        "期間": f"{monthly['exec_date'].iloc[0]} ~ {monthly['end_date'].iloc[-1]}",
        "月數": n,
        "年化報酬（扣成本）": ann_ret,
        "年化波動": ann_vol,
        "Sharpe（rf=0）": ann_ret / ann_vol if ann_vol > 0 else np.nan,
        "最大回撤（月頻）": mdd,
        "平均月換手率": monthly["turnover"].mean(),
        "年化成本拖累": monthly["cost_rate"].mean() * 12,
        "平均持股檔數": monthly["n_holdings"].mean(),
    }
    if b.notna().all():
        bnav = (1 + b).cumprod()
        b_ann = bnav.iloc[-1] ** (12 / n) - 1
        out["Benchmark 年化報酬"] = b_ann
        out["年化超額報酬"] = ann_ret - b_ann
    return out


def format_summary(summary: dict) -> str:
    pct_keys = {"年化報酬（扣成本）", "年化波動", "最大回撤（月頻）", "平均月換手率",
                "年化成本拖累", "Benchmark 年化報酬", "年化超額報酬"}
    lines = ["=" * 40, "回測績效摘要", "=" * 40]
    for k, v in summary.items():
        if k in pct_keys:
            lines.append(f"{k:<16}{v:>10.2%}")
        elif isinstance(v, float):
            lines.append(f"{k:<16}{v:>10.2f}")
        else:
            lines.append(f"{k:<16}{v!s:>10}")
    return "\n".join(lines)
