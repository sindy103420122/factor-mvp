from __future__ import annotations
import argparse, csv, hashlib, json, os, time, urllib.parse, urllib.request
from datetime import datetime, timezone
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / 'data' / 'raw'
START, END = '2015-01-01', '2026-10-01'
TICKERS = ['2330','2317','2454','2308','2881','2882','2886','2891','2303','3711','6505','2412']
DATASETS = ['TaiwanStockPrice','TaiwanStockFinancialStatements','TaiwanStockBalanceSheet','TaiwanStockMonthRevenue','TaiwanStockDividend','TaiwanStockDividendResult']

def fetch_json(url: str, tries=5):
    last=None
    for attempt in range(tries):
        hosts=['www.twse.com.tw','wwwc.twse.com.tw'] if 'twse.com.tw/' in url else [None]
        for host in hosts:
            target=url.replace('www.twse.com.tw',host) if host else url
            try:
                headers={'User-Agent':'Mozilla/5.0 TaiwanFactorMVP/1.0'}
                if host: headers['Referer']='https://www.twse.com.tw/'
                req=urllib.request.Request(target,headers=headers)
                return json.loads(urllib.request.urlopen(req,timeout=45).read().decode('utf-8-sig'))
            except Exception as e: last=e
        time.sleep(1+attempt)
    raise RuntimeError(f'Failed to retrieve {url}: {last}')

def save_rows(rows, path: Path):
    pd.DataFrame(rows).to_csv(path,index=False,encoding='utf-8-sig')

def main(refresh=False):
    RAW.mkdir(parents=True,exist_ok=True)
    for ticker in TICKERS:
        for ds in DATASETS:
            path=RAW/f'finmind_{ds}_{ticker}_{START}_{END}.csv'
            if path.exists() and not refresh:
                print(f'cached {ds} {ticker}',flush=True); continue
            q=urllib.parse.urlencode({'dataset':ds,'data_id':ticker,'start_date':START,'end_date':END})
            payload=fetch_json('https://api.finmindtrade.com/api/v4/data?'+q)
            if payload.get('status')!=200: raise RuntimeError(f'{ticker} {ds}: {payload}')
            rows=payload.get('data',[])
            if not rows and ds in ('TaiwanStockPrice','TaiwanStockFinancialStatements','TaiwanStockBalanceSheet'):
                print(f'WARNING empty {ds} {ticker}',flush=True)
            save_rows(rows,path); print(f'downloaded {ds} {ticker}: {len(rows):,}',flush=True); time.sleep(.12)

    # Checkpoint by month so a network failure can be resumed without losing prior downloads.
    index_path=RAW/'twse_taiex_total_return_daily_2015-01_2026-09.csv'
    existing=[]; covered=set()
    if index_path.exists():
        old=pd.read_csv(index_path,encoding='utf-8-sig')
        existing=old.to_dict('records')
        covered={pd.Period(str(r['date'])[:7],freq='M') for r in existing}
    rows=list(existing)
    months=pd.period_range('2015-01','2026-09',freq='M')
    for i,m in enumerate(months,1):
        if m in covered: continue
        q=urllib.parse.urlencode({'date':m.strftime('%Y%m')+'01','response':'json'})
        payload=fetch_json('https://www.twse.com.tw/indicesReport/MFI94U?'+q)
        if payload.get('stat')!='OK': raise RuntimeError(f'TWSE {m}: {payload}')
        for row in payload.get('data',[]):
            y,mo,d=map(int,row[0].split('/'))
            rows.append({'date':f'{y+1911:04d}-{mo:02d}-{d:02d}','total_return_index':float(row[1].replace(',',''))})
        save_rows(pd.DataFrame(rows).drop_duplicates('date').sort_values('date').to_dict('records'),index_path)
        covered.add(m); print(f'downloaded TWSE total-return month {m} ({i}/{len(months)})',flush=True); time.sleep(.1)

    files=[]
    for path in sorted(RAW.glob('*.csv')):
        h=hashlib.sha256(path.read_bytes()).hexdigest()
        files.append({'file':str(path.relative_to(ROOT)).replace('\\','/'),'rows':max(sum(1 for _ in path.open(encoding='utf-8-sig'))-1,0),'sha256':h})
    manifest={'as_of_utc':datetime.now(timezone.utc).isoformat(),'window':[START,END],'equities':TICKERS,'provider':'FinMind public API v4 for stock data; TWSE official MFI94U monthly endpoint for TAIEX total-return levels','files':files,'limitations':['Universe is a hand-picked sample of currently listed liquid stocks, not point-in-time historical constituents; survivorship and selection bias remain.','Prices are raw daily closes; corporate-action-adjusted returns must be constructed and validated before strategy evaluation.','Financial statement period dates are not publication timestamps; point-in-time joins are required before using fundamentals in historical signals.','FinMind Free access is non-commercial; check provider terms before commercial use or redistribution.']}
    (RAW/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
    print(f'FINISHED: {len(files)} CSV files; {len(pd.read_csv(index_path)):,} benchmark rows.',flush=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser(); parser.add_argument('--refresh',action='store_true',help='Redownload cached stock files')
    main(refresh=parser.parse_args().refresh)

