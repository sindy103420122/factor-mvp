from __future__ import annotations
import argparse, json
from pathlib import Path
import numpy as np
import pandas as pd

# Five fully price-derived signals: momentum (2), reversal (1), defensive (1), liquidity (1).
FACTORS = {"momentum": ["mom_12_1", "mom_6_1"], "reversal": ["reversal_1m"], "defensive": ["low_vol_12m"], "liquidity": ["liquidity_60d"]}
REQUIRED = ["month", "ticker", "investable", "next_return", "benchmark_return", *[x for xs in FACTORS.values() for x in xs]]


def load_panel(path: str | Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    missing = sorted(set(REQUIRED) - set(df.columns))
    if missing: raise ValueError(f"Missing required columns: {missing}")
    df["month"] = pd.to_datetime(df["month"]).dt.to_period("M").dt.to_timestamp("M")
    if df.duplicated(["month", "ticker"]).any(): raise ValueError("Duplicate month/ticker rows")
    if not df["next_return"].between(-1, 5).all(): raise ValueError("Returns must be decimal returns, not percentages")
    if df["benchmark_return"].isna().any(): raise ValueError("Benchmark total returns are required each month")
    return df.sort_values(["month", "ticker"]).reset_index(drop=True)


def _zscore(s: pd.Series) -> pd.Series:
    x = s.astype(float); sd = x.std(ddof=0)
    return (x - x.mean()) / sd if pd.notna(sd) and sd > 1e-12 else pd.Series(0.0, index=s.index)


def score_month(g: pd.DataFrame, method: str, history: dict[str, list[float]]) -> pd.DataFrame:
    x = g.loc[g.investable.astype(bool)].copy()
    factors = [f for fs in FACTORS.values() for f in fs]
    for f in factors:
        vals=x[f].replace([np.inf,-np.inf],np.nan)
        x[f"z_{f}"]=_zscore(vals.fillna(vals.median() if vals.notna().any() else 0.0))
    if method == "baseline":
        weights={f:1/len(factors) for f in factors}
    elif method == "smart":
        raw={}
        for f in factors:
            prior=history.get(f,[])[-36:]
            raw[f]=max(float(np.mean(prior)),0.0) if len(prior)>=12 else 1.0
        total=sum(raw.values()) or len(raw)
        weights={f:raw[f]/total for f in factors}
    else: raise ValueError("method must be baseline or smart")
    x["score"]=sum(x[f"z_{f}"]*weights[f] for f in factors)
    return x.sort_values(["score","ticker"],ascending=[False,True])


def metrics(r: pd.Series, turnover: pd.Series | None = None) -> dict:
    r=r.dropna().astype(float)
    if r.empty: return {"months":0,"total_return":None,"cagr":None,"volatility":None,"sharpe_rf0":None,"max_drawdown":None,"avg_one_way_turnover":None}
    wealth=(1+r).cumprod(); years=len(r)/12
    cagr=wealth.iloc[-1]**(1/years)-1 if years else np.nan
    vol=r.std(ddof=1)*np.sqrt(12) if len(r)>1 else np.nan
    sharpe=r.mean()*12/vol if pd.notna(vol) and vol>0 else np.nan
    dd=wealth/wealth.cummax()-1
    return {"months":int(len(r)),"total_return":float(wealth.iloc[-1]-1),"cagr":float(cagr),"volatility":float(vol),"sharpe_rf0":float(sharpe),"max_drawdown":float(dd.min()),"avg_one_way_turnover":float(turnover.mean()) if turnover is not None and len(turnover) else None}


def backtest(df: pd.DataFrame, method="baseline", top_n=5, fee_bps=14.25, tax_bps=30.0, slippage_bps=10.0):
    factors=[f for fs in FACTORS.values() for f in fs]
    history={f:[] for f in factors}; prev_weights={}; records=[]; ranks=[]
    for month,g in df.groupby("month",sort=True):
        ranked=score_month(g,method,history); selected=ranked.head(top_n)
        n=len(selected); curr_weights={t:1/n for t in selected.ticker} if n else {}
        universe=set(prev_weights)|set(curr_weights)
        buys=sum(max(curr_weights.get(t,0)-prev_weights.get(t,0),0) for t in universe)
        sells=sum(max(prev_weights.get(t,0)-curr_weights.get(t,0),0) for t in universe)
        turnover=max(buys,sells) # one-way traded fraction of NAV
        buy_rate=(fee_bps+slippage_bps)/10000
        sell_rate=(fee_bps+tax_bps+slippage_bps)/10000
        cost=buys*buy_rate+sells*sell_rate
        gross=float(sum(row.next_return*curr_weights[row.ticker] for row in selected.itertuples())) if n else 0.0
        net=(1+gross)*(1-cost)-1
        bm=float(g.benchmark_return.iloc[0])
        records.append({"month":month,"gross_return":gross,"net_return":net,"turnover_one_way":turnover,"buys":buys,"sells":sells,"cost":cost,"benchmark_return":bm,"holdings":n})
        if n: ranks.append(selected.assign(month=month,weight=1/n))
        # Score first; only after the holding month is complete can this IC enter future weights.
        tradable=g.loc[g.investable.astype(bool)]
        for f in history:
            pair=tradable[[f,"next_return"]].replace([np.inf,-np.inf],np.nan).dropna()
            ic=pair[f].rank().corr(pair.next_return.rank()) if len(pair)>=5 else np.nan
            if pd.notna(ic): history[f].append(float(ic))
        # Carry post-return weights into next month so the next rebalance cost reflects drift.
        post_values = {
            row.ticker: curr_weights[row.ticker] * (1 + row.next_return)
            for row in selected.itertuples()
        } if n else {}
        post_total = sum(post_values.values())
        prev_weights = {t: v / post_total for t, v in post_values.items()} if post_total > 0 else {}
    return pd.DataFrame(records),pd.concat(ranks,ignore_index=True) if ranks else pd.DataFrame()


def run(panel: str, outdir: str, top_n=5, fee_bps=14.25, tax_bps=30., slippage_bps=10.):
    df=load_panel(panel); out=Path(outdir); out.mkdir(parents=True,exist_ok=True); results={}
    for method in ("baseline","smart"):
        rets,holdings=backtest(df,method,top_n,fee_bps,tax_bps,slippage_bps)
        rets.to_csv(out/f"{method}_monthly.csv",index=False); holdings.to_csv(out/f"{method}_holdings.csv",index=False)
        for name,mask in [("development",rets.month<"2023-01-01"),("out_of_sample",(rets.month>="2023-01-01")&(rets.month<="2026-09-30"))]:
            r=rets.loc[mask]; results.setdefault(method,{})[name]={"strategy":metrics(r.net_return,r.turnover_one_way),"benchmark":metrics(r.benchmark_return)}
    (out/"summary.json").write_text(json.dumps({"methods":{"baseline":{"factor_weights":"equal","top_n":top_n},"smart":{"factor_weights":"trailing nonnegative mean rank IC; min 12 obs; max 36 obs","top_n":top_n}},"cost_assumptions_bps":{"commission_each_side":fee_bps,"sell_tax":tax_bps,"slippage_each_side":slippage_bps},"results":results,"caveat":"Exploratory 12-current-large-cap sample; not a point-in-time full-market result."},indent=2),encoding="utf-8")

if __name__=="__main__":
    p=argparse.ArgumentParser(description="Monthly Taiwan equity factor backtest")
    p.add_argument("--panel",required=True);p.add_argument("--out",default="reports/run");p.add_argument("--top-n",type=int,default=5);p.add_argument("--fee-bps",type=float,default=14.25);p.add_argument("--tax-bps",type=float,default=30);p.add_argument("--slippage-bps",type=float,default=10)
    a=p.parse_args();run(a.panel,a.out,a.top_n,a.fee_bps,a.tax_bps,a.slippage_bps)


