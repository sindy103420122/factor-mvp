from __future__ import annotations
import json, hashlib
from pathlib import Path
import numpy as np
import pandas as pd
from backtest import FACTORS

ROOT=Path(__file__).resolve().parents[1]; RAW=ROOT/'data'/'raw'; OUT=ROOT/'data'/'panel.csv'
TICKERS=['2330','2317','2454','2308','2881','2882','2886','2891','2303','3711','6505','2412']
START_MONTH=pd.Period('2016-01','M'); END_MONTH=pd.Period('2026-09','M')
MIN_AVG_VALUE=20_000_000

def read_csv(p): return pd.read_csv(p,encoding='utf-8-sig')

def adjusted_daily(ticker):
    price=read_csv(RAW/f'finmind_TaiwanStockPrice_{ticker}_2015-01-01_2026-10-01.csv')
    div=read_csv(RAW/f'finmind_TaiwanStockDividendResult_{ticker}_2015-01-01_2026-10-01.csv')
    price['date']=pd.to_datetime(price.date); price=price.sort_values('date').copy()
    price['adj_factor']=1.0
    for r in div.itertuples():
        if pd.isna(r.before_price) or pd.isna(r.after_price) or r.before_price<=0 or r.after_price<=0: continue
        exdate=pd.to_datetime(r.date)
        price.loc[price.date<exdate,'adj_factor']*=float(r.after_price)/float(r.before_price)
    for c in ['open','close']:
        price[c]=pd.to_numeric(price[c],errors='coerce')
    price['adj_close']=price.close*price.adj_factor
    price['adj_open']=price.open*price.adj_factor
    price['Trading_money']=pd.to_numeric(price.Trading_money,errors='coerce')
    return price

def main():
    idx=read_csv(RAW/'twse_taiex_total_return_daily_2015-01_2026-09.csv'); idx.date=pd.to_datetime(idx.date); idx=idx.sort_values('date')
    idxm=idx.set_index('date').total_return_index.resample('ME').last().dropna()
    benchmark=idxm.pct_change()
    monthly_frames=[]
    for ticker in TICKERS:
        d=adjusted_daily(ticker).set_index('date').sort_index()
        mclose=d.adj_close.resample('ME').last()
        mfirst_open=d.adj_open.resample('MS').first() # month-start labels
        mlast_close=d.adj_close.resample('ME').last()
        # Aggregate monthly bars indexed at month-end and use next month's first session open as entry.
        first_open=d.adj_open.groupby(d.index.to_period('M')).first()
        first_open.index=first_open.index.to_timestamp('M')
        last_close=mlast_close
        # Signals known at prior month-end, returns from next month's first open through its last close.
        mom121=(mclose.shift(1)/mclose.shift(12)-1)
        mom61=(mclose.shift(1)/mclose.shift(6)-1)
        reversal=-(mclose.shift(1)/mclose.shift(2)-1)
        daily_ret=d.adj_close.pct_change()
        vol=daily_ret.rolling(252,min_periods=200).std()*np.sqrt(252)
        vol_m=vol.resample('ME').last()
        value60=d.Trading_money.rolling(60,min_periods=40).mean()
        value60_m=value60.resample('ME').last()
        # Reindex the prior-month-end signals to the holding month-end.
        for hold_month in pd.period_range(START_MONTH,END_MONTH,freq='M'):
            m_end=hold_month.to_timestamp('M'); prev_end=(hold_month-1).to_timestamp('M')
            if m_end not in last_close.index or prev_end not in mclose.index: continue
            px_open=first_open.get(m_end,np.nan); px_close=last_close.get(m_end,np.nan)
            if pd.isna(px_open) or pd.isna(px_close) or px_open<=0: continue
            if m_end not in benchmark.index or pd.isna(benchmark.loc[m_end]): continue
            avg_value=value60_m.get(prev_end,np.nan)
            first_seen=d.index.min()
            months_listed=(prev_end.to_period('M')-first_seen.to_period('M')).n+1
            row={'month':m_end,'ticker':ticker,'mom_12_1':mom121.get(prev_end,np.nan),'mom_6_1':mom61.get(prev_end,np.nan),'reversal_1m':reversal.get(prev_end,np.nan),'low_vol_12m':-vol_m.get(prev_end,np.nan),'liquidity_60d':np.log(avg_value) if pd.notna(avg_value) and avg_value>0 else np.nan,'avg_value_60d':avg_value,'investable':bool(pd.notna(avg_value) and avg_value>=MIN_AVG_VALUE and months_listed>=12),'next_return':px_close/px_open-1,'benchmark_return':benchmark.loc[m_end]}
            monthly_frames.append(row)
    panel=pd.DataFrame(monthly_frames)
    factor_names=[f for group in FACTORS.values() for f in group]
    panel=panel.dropna(subset=['next_return','benchmark_return'])
    panel=panel.sort_values(['month','ticker']).reset_index(drop=True)
    OUT.parent.mkdir(parents=True,exist_ok=True); panel.to_csv(OUT,index=False,encoding='utf-8-sig')
    stats={'rows':len(panel),'stocks':sorted(panel.ticker.unique().tolist()),'first_month':panel.month.min().strftime('%Y-%m'),'last_month':panel.month.max().strftime('%Y-%m'),'monthly_rows':int(panel.month.nunique()),'investable_counts':panel.groupby('month').investable.sum().describe().to_dict(),'factor_missing_share':panel[factor_names].isna().mean().to_dict(),'min_avg_trading_value_twd':MIN_AVG_VALUE,'corporate_action_method':'Backward-adjusted prior prices by TWSE reference after/before ratio from FinMind TaiwanStockDividendResult; custom approximate total-return adjustment.'}
    (OUT.parent/'panel_qc.json').write_text(json.dumps(stats,indent=2,default=str),encoding='utf-8')
    print(json.dumps(stats,indent=2,default=str))
if __name__=='__main__': main()


