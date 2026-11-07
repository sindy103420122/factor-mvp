from __future__ import annotations
import json, math
from pathlib import Path
import numpy as np
import pandas as pd
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, Flowable, KeepTogether

ROOT=Path(__file__).resolve().parents[1]
REPORTS=ROOT/'reports'; RUN=REPORTS/'run'; DATA=ROOT/'data'
PDF=REPORTS/'台股智慧因子回測報告.pdf'; MD=REPORTS/'backtest_report.md'

def pct(x,dec=1): return 'N/A' if x is None or pd.isna(x) else f'{x*100:.{dec}f}%'
def num(x,dec=2): return 'N/A' if x is None or pd.isna(x) else f'{x:.{dec}f}'
def fmt_twd(x): return f'{x/1e6:.1f} 百萬元'

panel=pd.read_csv(DATA/'panel.csv',parse_dates=['month'])
summary=json.loads((RUN/'summary.json').read_text(encoding='utf-8'))
base=pd.read_csv(RUN/'baseline_monthly.csv',parse_dates=['month'])
smart=pd.read_csv(RUN/'smart_monthly.csv',parse_dates=['month'])
bh=pd.read_csv(RUN/'baseline_holdings.csv',parse_dates=['month'])
sh=pd.read_csv(RUN/'smart_holdings.csv',parse_dates=['month'])
manifest=json.loads((DATA/'raw'/'manifest.json').read_text(encoding='utf-8'))
idx=pd.read_csv(DATA/'raw'/'twse_taiex_total_return_daily_2015-01_2026-09.csv',parse_dates=['date'])

# Summary tables use the saved, single frozen run; no OOS parameter search is performed here.
annual=[]
for year in sorted(base.month.dt.year.unique()):
    row={'year':year}
    for name,df,col in [('Baseline',base,'net_return'),('Smart IC',smart,'net_return'),('TAIEX TR',base,'benchmark_return')]:
        x=df[df.month.dt.year==year][col]
        row[name]=float((1+x).prod()-1) if len(x) else np.nan
    row['period']='截至9月' if year==2026 else ''
    annual.append(row)
annual_df=pd.DataFrame(annual)
annual_df.to_csv(REPORTS/'annual_returns.csv',index=False,encoding='utf-8-sig')

factor_cols=['mom_12_1','mom_6_1','reversal_1m','low_vol_12m','liquidity_60d']
factor_names={'mom_12_1':'12-1 動能','mom_6_1':'6-1 動能','reversal_1m':'近月反轉','low_vol_12m':'低波動','liquidity_60d':'流動性'}
ic_rows=[]
for label,mask in [('開發期',(panel.month>='2016-01-01')&(panel.month<='2022-12-31')),('樣本外',(panel.month>='2023-01-01')&(panel.month<='2026-09-30'))]:
    p=panel.loc[mask & panel.investable.astype(bool)]
    for f in factor_cols:
        vals=[]
        for _,g in p.groupby('month'):
            q=g[[f,'next_return']].replace([np.inf,-np.inf],np.nan).dropna()
            if len(q)>=5:
                v=q[f].rank().corr(q.next_return.rank())
                if pd.notna(v): vals.append(v)
        ic_rows.append({'period':label,'factor':f,'mean_rank_ic':float(np.mean(vals)) if vals else np.nan,'positive_month_share':float(np.mean(np.array(vals)>0)) if vals else np.nan,'months':len(vals)})
ic_df=pd.DataFrame(ic_rows); ic_df.to_csv(REPORTS/'factor_ic.csv',index=False,encoding='utf-8-sig')

# Top holding frequency and trading-cost summaries.
concentration=[]
for label,h in [('Baseline',bh),('Smart IC',sh)]:
    o=h[(h.month>='2023-01-01')&(h.month<='2026-09-30')]
    counts=o.groupby('ticker').size().sort_values(ascending=False)
    for ticker,count in counts.items():
        concentration.append({'strategy':label,'ticker':ticker,'months_held':int(count),'share_of_stock_months':float(count/max(len(o),1))})
conc_df=pd.DataFrame(concentration); conc_df.to_csv(REPORTS/'oos_holdings_frequency.csv',index=False,encoding='utf-8-sig')

qc=json.loads((DATA/'panel_qc.json').read_text(encoding='utf-8'))
methods=summary['results']
period_defs=[('開發期','development'),('樣本外','out_of_sample')]
metric_rows=[]
for label,key in period_defs:
    for method,display in [('baseline','Baseline 等權因子'),('smart','Smart 滾動 IC'),('benchmark','TAIEX 含息')]:
        source=methods['baseline'][key]['benchmark'] if method=='benchmark' else methods[method][key]['strategy']
        metric_rows.append({'period':label,'name':display,**source})
metrics_df=pd.DataFrame(metric_rows);metrics_df.to_csv(REPORTS/'performance_metrics.csv',index=False,encoding='utf-8-sig')

def series_metrics(df,col):
    r=df[col].astype(float);wealth=(1+r).cumprod();peak=wealth.cummax();dd=wealth/peak-1
    return {'total':float(wealth.iloc[-1]-1),'cagr':float(wealth.iloc[-1]**(12/len(r))-1),'vol':float(r.std(ddof=1)*np.sqrt(12)),'sharpe':float(r.mean()*12/(r.std(ddof=1)*np.sqrt(12))),'mdd':float(dd.min())}

# Dataset counts from raw CSV sizes/manifest.
dataset_counts={}
for item in manifest['files']:
    key=item['file'].split('/')[-1].split('_')[1] if item['file'].split('/')[-1].startswith('finmind_') else 'TWSE_INDEX'
    dataset_counts[key]=dataset_counts.get(key,0)+item['rows']

def returns_to_wealth(s): return (1+s).cumprod()

class EquityChart(Flowable):
    def __init__(self,series,title,ylabel='資產倍數',height=75*mm,phase_marker=None):
        Flowable.__init__(self);self.series=series;self.title=title;self.ylabel=ylabel;self.height=height;self.width=172*mm;self.phase_marker=phase_marker
    def wrap(self,aw,ah): self.width=aw;return aw,self.height
    def draw(self):
        c=self.canv; w=self.width;h=self.height; ml=19*mm;mr=7*mm;mt=20*mm;mb=13*mm
        x0=ml;y0=mb;pw=w-ml-mr;ph=h-mt-mb
        c.setFont('Body',10);c.setFillColor(colors.HexColor('#183451'));c.drawString(0,h-5*mm,self.title)
        allv=np.concatenate([np.asarray(v[1],dtype=float) for v in self.series.values()]);ymin=float(np.nanmin(allv));ymax=float(np.nanmax(allv));
        if ymax-ymin<1e-8:ymax=ymin+1
        pad=(ymax-ymin)*.08;ymin-=pad;ymax+=pad
        c.setStrokeColor(colors.HexColor('#D8E0EA'));c.setLineWidth(.4)
        for k in range(5):
            yy=y0+ph*k/4;val=ymin+(ymax-ymin)*k/4;c.line(x0,yy,x0+pw,yy);c.setFont('Body',7);c.setFillColor(colors.HexColor('#5B6570'));c.drawRightString(x0-2*mm,yy-2,val*100 and (f'{val:.1f}' if self.ylabel=='資產倍數' else f'{val:.0%}'))
        for ser_i,(name,(dates,values,color)) in enumerate(self.series.items()):
            vals=np.asarray(values,dtype=float);n=len(vals)
            if not n:continue
            c.setStrokeColor(colors.HexColor(color));c.setLineWidth(1.7)
            path=c.beginPath()
            for i,v in enumerate(vals):
                xx=x0+(pw*i/max(n-1,1)); yy=y0+ph*(v-ymin)/(ymax-ymin)
                if i==0:path.moveTo(xx,yy)
                else:path.lineTo(xx,yy)
            c.drawPath(path)
            lx=x0+ser_i*38*mm;c.setStrokeColor(colors.HexColor(color));c.line(lx,h-13*mm,lx+5*mm,h-13*mm);c.setFillColor(colors.HexColor('#304254'));c.setFont('Body',7.5);c.drawString(lx+6*mm,h-14*mm,name)
        if self.phase_marker is not None and len(self.series):
            dates=next(iter(self.series.values()))[0];pos=self.phase_marker
            if 0<=pos<len(dates):
                xx=x0+pw*pos/max(len(dates)-1,1);c.setStrokeColor(colors.HexColor('#7A8794'));c.setDash(2,2);c.line(xx,y0,xx,y0+ph);c.setDash()
        c.setFillColor(colors.HexColor('#5B6570'));c.setFont('Body',7)
        if self.series:
            dates=next(iter(self.series.values()))[0]
            if len(dates): c.drawString(x0,y0-6*mm,str(pd.Timestamp(dates[0]).strftime('%Y-%m')));c.drawRightString(x0+pw,y0-6*mm,str(pd.Timestamp(dates[-1]).strftime('%Y-%m')))

def page_footer(canvas,doc):
    canvas.saveState();w,h=A4
    canvas.setStrokeColor(colors.HexColor('#D5DDE7'));canvas.setLineWidth(.4);canvas.line(18*mm,14*mm,w-18*mm,14*mm)
    canvas.setFont('Body',7.5);canvas.setFillColor(colors.HexColor('#697586'))
    canvas.drawString(18*mm,9*mm,'台股智慧因子回測｜探索性研究，非投資建議')
    canvas.drawRightString(w-18*mm,9*mm,f'{doc.page}')
    canvas.restoreState()

# Register traditional Chinese font.
pdfmetrics.registerFont(TTFont('Body','C:/Windows/Fonts/msjh.ttc',subfontIndex=0))
pdfmetrics.registerFont(TTFont('Bold','C:/Windows/Fonts/msjhbd.ttc',subfontIndex=0))
styles=getSampleStyleSheet()
styles.add(ParagraphStyle(name='TitleC',fontName='Bold',fontSize=24,leading=32,textColor=colors.HexColor('#173B63'),alignment=TA_CENTER,spaceAfter=8))
styles.add(ParagraphStyle(name='SubC',fontName='Body',fontSize=11,leading=17,textColor=colors.HexColor('#5A6B7D'),alignment=TA_CENTER,spaceAfter=4))
styles.add(ParagraphStyle(name='H1C',fontName='Bold',fontSize=17,leading=24,textColor=colors.HexColor('#173B63'),spaceBefore=2,spaceAfter=8))
styles.add(ParagraphStyle(name='H2C',fontName='Bold',fontSize=11,leading=16,textColor=colors.HexColor('#23619A'),spaceBefore=5,spaceAfter=4))
styles.add(ParagraphStyle(name='BodyC',fontName='Body',fontSize=9.2,leading=14,textColor=colors.HexColor('#243342'),spaceAfter=5))
styles.add(ParagraphStyle(name='SmallC',fontName='Body',fontSize=7.4,leading=10.5,textColor=colors.HexColor('#526170'),spaceAfter=3))
styles.add(ParagraphStyle(name='CalloutC',fontName='Bold',fontSize=10,leading=15,textColor=colors.HexColor('#173B63'),backColor=colors.HexColor('#EDF4FB'),borderColor=colors.HexColor('#CBDCF0'),borderWidth=.6,borderPadding=8,spaceBefore=5,spaceAfter=7))
styles.add(ParagraphStyle(name='TableC',fontName='Body',fontSize=7.4,leading=10,textColor=colors.HexColor('#243342')))
styles.add(ParagraphStyle(name='TableHeadC',fontName='Bold',fontSize=7.4,leading=10,textColor=colors.white))

def P(t,style='BodyC'): return Paragraph(t,styles[style])
def make_table(rows,widths,header=True,align='LEFT',font=7.4):
    wrapped=[]
    for ri,row in enumerate(rows):
        wrapped.append([Paragraph(str(v),styles['TableHeadC'] if header and ri==0 else styles['TableC']) for v in row])
    t=Table(wrapped,colWidths=widths,repeatRows=1 if header else 0,hAlign=align)
    cmds=[('VALIGN',(0,0),(-1,-1),'MIDDLE'),('LEFTPADDING',(0,0),(-1,-1),5),('RIGHTPADDING',(0,0),(-1,-1),5),('TOPPADDING',(0,0),(-1,-1),4),('BOTTOMPADDING',(0,0),(-1,-1),4),('GRID',(0,0),(-1,-1),.35,colors.HexColor('#D2DCE7'))]
    if header:cmds += [('BACKGROUND',(0,0),(-1,0),colors.HexColor('#285A8E'))]
    for r in range(1 if header else 0,len(rows)):
        if r%2==0:cmds.append(('BACKGROUND',(0,r),(-1,r),colors.HexColor('#F3F6FA')))
    t.setStyle(TableStyle(cmds));return t

flow=[]
# Page 1: Executive cover
flow += [Spacer(1,14*mm),P('台股智慧因子投資','TitleC'),P('月頻策略回測報告','TitleC'),P('12 檔現存大型股樣本｜含息基準｜交易成本後績效','SubC'),Spacer(1,7*mm),P('報告期間：2016/01-2026/09　｜　開發：2016/01-2022/12　｜　樣本外：2023/01-2026/09','SubC'),Spacer(1,11*mm)]
ob=methods['baseline']['out_of_sample']['strategy']; bm=methods['baseline']['out_of_sample']['benchmark']; os=methods['smart']['out_of_sample']['strategy']
headline=[['樣本外指標','Baseline 等權','Smart 滾動 IC','TAIEX 含息'],['年化報酬',pct(ob['cagr']),pct(os['cagr']),pct(bm['cagr'])],['年化波動',pct(ob['volatility']),pct(os['volatility']),pct(bm['volatility'])],['Sharpe（無風險利率 0%）',num(ob['sharpe_rf0']),num(os['sharpe_rf0']),num(bm['sharpe_rf0'])],['最大回撤',pct(ob['max_drawdown']),pct(os['max_drawdown']),pct(bm['max_drawdown'])]]
flow += [make_table(headline,[48*mm,36*mm,38*mm,35*mm]),Spacer(1,8*mm),P('投資人結論：樣本外兩種策略的年化報酬高於基準，但波動更高、Sharpe 較低，最大回撤也較深。開發期 baseline 略落後基準，smart 明顯落後。由於股票池是事後挑選的現存大型股，這些數字不能視為全市場可投資績效，也不足以支持實盤採用。','CalloutC'),P('核心限制：目前是 12 檔股票的探索性比較，不是原簡報所要求的全市場點時樣本外驗收。因子只用價格、波動與流動性資訊；沒有使用財報型價值/品質訊號。','BodyC'),Spacer(1,4*mm),P('資料來源：FinMind 台股價格、公司行動資料；TAIEX 總報酬指數取自 TWSE。原始資料、雜湊與回測輸出隨專案附上。','SmallC'),PageBreak()]

# Page 2: Scope and design
flow += [P('1. 研究問題與回測設計','H1C'),P('研究問題：五個可解釋的價格因子等權排序，是否能在月調倉與保守交易成本後，勝過台灣加權報酬指數？另比較 rolling-IC 權重能否優於固定等權。','BodyC'),P('時間切分','H2C'),make_table([['階段','日期','月份','用途'],['暖機期','2015/01-2015/12','12','提供 12 個月動能與波動估計資料'],['開發期','2016/01-2022/12','84','建立與比較兩個固定方法'],['固定樣本外','2023/01-2026/09','45','一次性驗收；未依其結果調參']], [28*mm,45*mm,18*mm,66*mm]),Spacer(1,5*mm),P('股票池與持倉','H2C'),P('股票池固定為 2330、2317、2454、2308、2881、2882、2886、2891、2303、3711、6505、2412。每月以過去 60 個交易日平均成交金額至少新台幣 2,000 萬元為門檻，選分數最高的 5 檔等權持有。大多數成分每月均通過門檻；3711 只在其資料與掛牌年限允許後進入。','BodyC'),P('兩個方法','H2C'),P('<b>Baseline：</b>五因子橫斷面 z-score 等權加總。<br/><b>Smart：</b>每個因子以過去最多 36 個月 Spearman rank IC 的非負均值作權重；最少 12 個有效 IC 前維持等權。每月先打分、當月持有報酬實現後才更新 IC，避免當期報酬洩漏。','BodyC'),P('月訊號於前一月末形成，持倉報酬由當月第一個交易日開盤至月末收盤估算。基準報酬採前月底至當月底的 TAIEX 總報酬指數；兩者在月初隔夜區間有輕微起點差異。','SmallC'),PageBreak()]

# Page 3 data audit
flow += [P('2. 資料與品質檢查','H1C'),P('來源與覆蓋','H2C'),make_table([['資料','涵蓋','用途'],['FinMind 個股日價','12 檔；最長 2015/01-2026/09；33,529 列','日價格、成交金額、技術因子'],['FinMind 財報/資產負債表/月營收/股利','12 檔；原始 CSV 及 manifest 隨附','本報告未用於因子計分；缺歷史公告可得日'],['FinMind 除權息結果','12 檔；2015/01-2026/09','以除權息參考價比率回溯調整日價'],['TWSE TAIEX 總報酬指數','2,861 個交易日；2015/01-2026/09','含息市場基準']], [35*mm,57*mm,65*mm]),Spacer(1,5*mm),P('資料處理','H2C'),P('個股價格由 FinMind 原始日收盤價建立近似總報酬調整序列。除權息日以前的歷史價格乘以官方參考價 after_price / before_price；調整後價格用於動能、反轉、低波動與月持有報酬。此為本專案自建近似法，並非供應商正式還原價，仍可能受減資、現增、資料更正與公司行動複雜情況影響。','BodyC'),P('關鍵偏誤','H2C'),P('1) <b>存活者與選樣偏誤：</b>12 檔是以目前大型/流動股票為樣本，排除了曾下市或曾不具代表性的公司。<br/>2) <b>非點時股票池：</b>沒有逐月歷史成分資料；流動性門檻只能在這 12 檔內運作。<br/>3) <b>財報前視風險：</b>原始財報列以財務期間為日期，缺完整歷史公開時間與修訂版本，因此不拿來產生 ROE、價值或成長因子。<br/>4) <b>交易限制：</b>未模擬停牌、漲跌停無法成交、開盤跳空、容量、零股、分割與現增細節。','BodyC'),P('所以這份報告數字可重現於附帶資料，不應解讀為代表全市場策略未來表現。FinMind 免費方案標示非商業用途；公開分享原始資料前須遵守其資料授權。','CalloutC'),PageBreak()]

# Page 4 factors
flow += [P('3. 因子定義與投資直覺','H1C'),P('五個訊號皆以月末已知價格/成交金額建立，並在當月橫斷面標準化。所有方向都設定為「數值愈高，排序愈前」。','BodyC')]
factors=[['類別','因子','計算方向','投資直覺 / 注意事項'],['動能','12-1 動能','前月末 / 12 個月前月末 - 1','捕捉中期價格延續，避開最近一個月反轉'],['動能','6-1 動能','前月末 / 6 個月前月末 - 1','較短的中期趨勢；與 12-1 有相關性'],['反轉','近月反轉','最近一個月報酬乘以 -1','捕捉短期過度反應回歸；換手與噪音可能較大'],['防禦','低波動','前 252 交易日標準差乘以 -1','偏好歷史波動較低的股票；不等於未來風險較低'],['流動性','流動性','前 60 日平均成交金額取自然對數','提高可交易性；小樣本中會偏向最大型股票']]
flow += [make_table(factors,[19*mm,27*mm,48*mm,63*mm]),Spacer(1,5*mm),P('因子資料不足如何處理','H2C'),P('五個因子全部使用價格與成交金額，達成至少五因子、至少三類別的 MVP 規格。沒有將價值、ROE 或營收成長塞進模型，因為現有歷史財報缺公告時點及修訂時間，會增加前視偏誤。這表示本報告測試的是「價格/流動性因子組合」，不是完整的基本面智慧因子產品。','BodyC'),P('每月在當月可投資股票中做 z-score；缺值用當月中位數補，若整項缺值則記 0。橫斷面只有約 11-12 檔，rank IC 權重估計非常不穩定，Smart 的比較應視為探索性。','BodyC'),P('所有收益皆採月頻；Sharpe 以無風險利率 0% 計算。CAGR 以各期間月數年化；最大回撤由該期間淨值曲線計。','SmallC'),PageBreak()]

# Page 5 performance
flow += [P('4. 主要績效結果','H1C'),P('以下策略績效已扣除佣金、賣出證交稅與滑價；TAIEX 為含息基準。單位為年化百分比，Sharpe 無風險利率設為 0%。','BodyC')]
perf=[['區間 / 組合','累積報酬','CAGR','年化波動','Sharpe','最大回撤','月單邊換手']]
for key,label in [('development','開發期'),('out_of_sample','樣本外')]:
 for meth,name in [('baseline','Baseline 等權'),('smart','Smart 滾動 IC'),('benchmark','TAIEX 含息')]:
  m=methods['baseline'][key]['benchmark'] if meth=='benchmark' else methods[meth][key]['strategy']
  perf.append([label+' / '+name,pct(m['total_return']),pct(m['cagr']),pct(m['volatility']),num(m['sharpe_rf0']),pct(m['max_drawdown']),pct(m.get('avg_one_way_turnover'))])
flow += [make_table(perf,[30*mm,24*mm,20*mm,24*mm,17*mm,24*mm,25*mm]),Spacer(1,5*mm),P('樣本外重點','H2C'),P(f"Baseline 的 CAGR 為 {pct(ob['cagr'])}，高於 TAIEX 的 {pct(bm['cagr'])}；Smart 為 {pct(os['cagr'])}。但兩個策略年化波動約 {pct(ob['volatility'])}-{pct(os['volatility'])}，高於基準 {pct(bm['volatility'])}；Sharpe 低於基準，最大回撤也更深。高報酬伴隨更高風險，且受樣本偏誤限制。",'BodyC'),P('開發期 baseline CAGR 為 '+pct(methods['baseline']['development']['strategy']['cagr'])+'，略低於基準 '+pct(methods['baseline']['development']['benchmark']['cagr'])+'；Smart CAGR 只有 '+pct(methods['smart']['development']['strategy']['cagr'])+'。Smart 並未在開發期建立勝過基準或 baseline 的證據。','BodyC'),P('累積報酬是樣本內外各自從 1.0 起算，不能串接比較。2026 年只到 9 月。','SmallC'),PageBreak()]

# Page 6 annual table and chart
flow += [P('5. 年度報酬與淨值路徑','H1C'),P('各年以月報酬幾何連乘；2026 僅計至 9 月。表內策略報酬為扣成本後，TAIEX 為含息指數。','BodyC')]
ann=[['年份','Baseline','Smart IC','TAIEX 含息']]
for r in annual:
 ann.append([str(r['year'])+('（1-9月）' if r['period'] else ''),pct(r['Baseline']),pct(r['Smart IC']),pct(r['TAIEX TR'])])
flow += [make_table(ann,[34*mm,38*mm,38*mm,40*mm]),Spacer(1,7*mm)]
all_dates=base.month.tolist(); ix=list(range(len(all_dates))); oos_pos=int(np.where(base.month>='2023-01-01')[0][0]) if any(base.month>='2023-01-01') else None
wealth_series={'Baseline':(all_dates,returns_to_wealth(base.net_return),'#2271B1'),'Smart IC':(all_dates,returns_to_wealth(smart.net_return),'#D17C00'),'TAIEX TR':(all_dates,returns_to_wealth(base.benchmark_return),'#4C956C')}
flow += [EquityChart(wealth_series,'全期間累積淨值（成本後；每條序列由 1.0 起算）','資產倍數',height=78*mm,phase_marker=oos_pos),Spacer(1,3*mm),P('垂直虛線為固定樣本外起點。圖表呈現單一 12 檔樣本；不能外推至全台股投資宇宙。','SmallC'),PageBreak()]

# Page 7 drawdowns and concentration
flow += [P('6. 風險、回撤與持倉集中','H1C'),P('年化波動與回撤顯示，樣本外超額 CAGR 不是無成本 alpha。Baseline OOS 的 Sharpe '+num(ob['sharpe_rf0'])+' 低於 TAIEX '+num(bm['sharpe_rf0'])+'；最大回撤 '+pct(ob['max_drawdown'])+' 深於 '+pct(bm['max_drawdown'])+'。Smart 的風險調整後績效也低於基準。','BodyC')]
def drawdown(s):
 w=(1+s).cumprod();return (w/w.cummax()-1)
dd_series={'Baseline':(all_dates,drawdown(base.net_return),'#2271B1'),'Smart IC':(all_dates,drawdown(smart.net_return),'#D17C00'),'TAIEX TR':(all_dates,drawdown(base.benchmark_return),'#4C956C')}
flow += [EquityChart(dd_series,'全期間回撤（每條序列各自計算）','percent',height=70*mm,phase_marker=oos_pos),Spacer(1,5*mm),P('樣本外持倉頻率：Baseline','H2C')]
top=conc_df[conc_df.strategy=='Baseline'].sort_values('months_held',ascending=False).head(6)
con_rows=[['代碼','持有月份','佔全部股票月']]+[[r.ticker,str(r.months_held),pct(r.share_of_stock_months)] for r in top.itertuples()]
flow += [make_table(con_rows,[35*mm,40*mm,55*mm]),Spacer(1,4*mm),P('每月等權、最多 5 檔，但樣本池本身只有 12 檔，產業曝險很容易集中。報告未使用歷史產業分類和全市場成分表，因此不對產業風險作過度推論。','SmallC'),PageBreak()]

# Page 8 factor diagnostics, smart-vs-baseline
flow += [P('7. 因子診斷與模型比較','H1C'),P('IC 是每月因子分數與同月持有報酬的橫斷面 Spearman rank correlation。下表為各期間月 IC 的平均與正值比例；樣本只有約 12 檔，統計噪音很大。樣本外 IC 僅作描述，不用來調參。','BodyC')]
ic_table=[['期間','因子','平均 Rank IC','正 IC 月比例','有效月數']]
for r in ic_df.itertuples(): ic_table.append([r.period,factor_names[r.factor],num(r.mean_rank_ic,3),pct(r.positive_month_share),str(r.months)])
flow += [make_table(ic_table,[27*mm,37*mm,34*mm,39*mm,26*mm]),Spacer(1,6*mm),P('Smart rolling IC 的結果','H2C'),P('Smart 權重設計是先驗不等於全等權的適應式方法；樣本內 84 個月後可以形成歷史 IC。其開發期 CAGR '+pct(methods['smart']['development']['strategy']['cagr'])+'，遠低於 baseline '+pct(methods['baseline']['development']['strategy']['cagr'])+' 和 TAIEX '+pct(methods['baseline']['development']['benchmark']['cagr'])+'。樣本外 Smart 也低於 baseline。這個樣本未顯示 rolling IC 有增值。','BodyC'),P('小型橫斷面、短樣本的 IC 權重容易被雜訊主導。若將模型換成更多因子、改視窗或門檻後再挑出勝出的 OOS，就會造成資料探勘偏誤；須另留未碰觸的未來樣本驗證。','CalloutC'),P('本報告沒有顯示因子權重熱圖，避免把少數股票算出的月度 IC 權重誤讀成穩定經濟因子溢酬。','SmallC'),PageBreak()]

# Page 9 conclusion and references
flow += [P('8. 結論、限制與下一步','H1C'),P('研究結論','H2C'),P('在此 12 檔現存大型股樣本中，Baseline 與 Smart 在 2023/01-2026/09 的年化報酬高於 TAIEX 含息指數；但二者承受更高波動、較低 Sharpe 和較深回撤。Baseline OOS 表現優於 Smart；Smart 未在開發期或樣本外證明其方法帶來穩健改善。這些結果只能說明本小樣本的歷史路徑，不能推導全市場 alpha。','BodyC'),P('投資人判斷','H2C'),P('不建議把這份樣本結果直接用於真實資金配置。全市場投資主張必須在加入下市股、點時成分股與財報公告日、正式還原價格、真實交易限制後重新評估。開發期 baseline 本就略輸基準，OOS 超額可能主要來自樣本選擇及 2023-2026 少數大型股強勢。','BodyC'),P('本次成本假設','H2C'),P('佣金每側 14.25 bps、賣出證交稅 30 bps、滑價每側 10 bps；依每月組合權重變化計算買入與賣出成本。實際券商折扣、股票類型稅率、成交量與跳空未完整校準，因此淨績效仍有模型風險。Sharpe 的無風險利率設為 0%。','BodyC'),P('後續若要升級為正式專案驗收','H2C'),P('1. 取得含上市、上櫃、下市股的逐月點時股票池和歷史市值/成交額。<br/>2. 使用公告日與修訂版本做財報 as-of join，才加入價值、品質或成長因子。<br/>3. 以供應商還原報酬/正式公司行動事件重做個股報酬。<br/>4. 增加漲跌停、停牌、開盤跳空、成本敏感度、年度/產業風險歸因。<br/>5. 冻結模型後，對新的、未觸碰樣本作最終驗收。','BodyC'),P('資料來源與可重現檔案','H2C'),P('FinMind：<link href="https://finmind.github.io/tutor/TaiwanMarket/Technical/" color="#23619A">台股價量、調整股價資料集</link>；<link href="https://finmind.github.io/tutor/TaiwanMarket/Fundamental/" color="#23619A">財報、除權息與下市資料集</link>。TWSE：<link href="https://www.twse.com.tw/indicesReport/MFI94U?date=20230101&response=json" color="#23619A">TAIEX 加權報酬指數月報表</link>。交易成本對因子策略的重要性可參考 <link href="https://ah.lib.nccu.edu.tw/item?item_id=165813&amp;locale=en" color="#23619A">政大台灣市場交易成本研究</link>。本報告的 monthly panel、月報酬、持股、IC、年度報酬 CSV 與 manifest 隨專案提供。','SmallC'),P('本文件為量化研究報告，不構成個人化投資建議。','SmallC')]

doc=SimpleDocTemplate(str(PDF),pagesize=A4,rightMargin=18*mm,leftMargin=18*mm,topMargin=16*mm,bottomMargin=20*mm,title='台股智慧因子投資月頻回測報告',author='OpenAI Codex')
doc.build(flow,onFirstPage=page_footer,onLaterPages=page_footer)

# Editable Markdown counterpart with the same key figures and methodology.
md=f'''# 台股智慧因子投資回測報告\n\n> **探索性 12 檔現存大型股樣本；非全市場點時回測，不可直接解讀為可投資績效。**\n\n報告期間：2016/01-2026/09；開發期 2016/01-2022/12（84 月）；樣本外 2023/01-2026/09（45 月）。2015 年為 12 個月動能暖機。\n\n## 摘要\n\n| 樣本外 | Baseline 等權 | Smart 滾動 IC | TAIEX 含息 |\n|---|---:|---:|---:|\n| CAGR | {pct(ob['cagr'])} | {pct(os['cagr'])} | {pct(bm['cagr'])} |\n| 年化波動 | {pct(ob['volatility'])} | {pct(os['volatility'])} | {pct(bm['volatility'])} |\n| Sharpe（無風險利率 0%） | {num(ob['sharpe_rf0'])} | {num(os['sharpe_rf0'])} | {num(bm['sharpe_rf0'])} |\n| 最大回撤 | {pct(ob['max_drawdown'])} | {pct(os['max_drawdown'])} | {pct(bm['max_drawdown'])} |\n| 累積報酬 | {pct(ob['total_return'])} | {pct(os['total_return'])} | {pct(bm['total_return'])} |\n\n樣本外兩種策略 CAGR 高於基準，但波動更高、Sharpe 更低且最大回撤更深。Baseline 在開發期 CAGR {pct(methods['baseline']['development']['strategy']['cagr'])}，低於基準 {pct(methods['baseline']['development']['benchmark']['cagr'])}；Smart 開發期 CAGR {pct(methods['smart']['development']['strategy']['cagr'])}。沒有證據顯示 Smart 增加價值。\n\n## 資料範圍與限制\n\n個股樣本：{', '.join(qc['stocks'])}。FinMind 日價與除權息結果、財報/資產負債表/月營收/股利；TAIEX 總報酬指數由 TWSE 取得，共 {len(idx):,} 日。panel 為 {qc['rows']:,} 股票月、{qc['monthly_rows']} 個月份。平均每月可投資股票 {qc['investable_counts']['mean']:.1f} 檔，持有前 5 檔。\n\n股價以除權息日官方參考價 after_price / before_price 比率回溯調整，作為近似總報酬價格。財報資料日期是財務期間、欠缺歷史公開時點與修訂版本，因此未用財報型因子。股票池是目前大型/流動股回看歷史，存在存活者與選樣偏誤；這不是全市場無偏回測。\n\n## 五因子\n\n1. 12-1 動能；2. 6-1 動能；3. 近月反轉（最近一月報酬取負）；4. 252 日低波動（標準差取負）；5. 60 日流動性（平均成交金額對數）。涵蓋動能、反轉、防禦、流動性四類。全部每月橫斷面 z-score，Baseline 五因子等權。Smart 使用過去最多 36 月非負平均 rank IC；至少 12 個歷史有效觀測才啟用適應權重。\n\n## 成本與執行\n\n佣金每側 14.25 bps、賣出證交稅 30 bps、滑價每側 10 bps。每月前一月底形成信號，於當月第一個交易日開盤估計建倉，月底收盤計價；基準採前月底至當月底含息報酬，因此月初隔夜起點存在輕微不一致。未模擬漲跌停、停牌、容量及市場衝擊。Sharpe 無風險利率設 0%。\n\n## 年度報酬\n\n| 年度 | Baseline | Smart IC | TAIEX 含息 |\n|---|---:|---:|---:|\n'''+''.join(f"| {int(r['year'])}{' (1-9月)' if r['period'] else ''} | {pct(r['Baseline'])} | {pct(r['Smart IC'])} | {pct(r['TAIEX TR'])} |\n" for r in annual)+'''\n## 結論\n\n不建議將此結果直接用於真實資金配置。要完成全市場正式驗收，需加入含下市股的點時股票池、財報公告日及修訂版本、正式調整後總報酬價格，並處理實際成交限制。所有結果 CSV、IC、年度表、持股及來源雜湊在專案 `reports/` 與 `data/raw/manifest.json`。\n\n資料來源：[FinMind 技術面資料](https://finmind.github.io/tutor/TaiwanMarket/Technical/)、[FinMind 基本面資料](https://finmind.github.io/tutor/TaiwanMarket/Fundamental/)、[TWSE TAIEX 總報酬指數](https://www.twse.com.tw/indicesReport/MFI94U?date=20230101&response=json)。本報告不構成投資建議。\n'''
MD.write_text(md,encoding='utf-8')
print(json.dumps({'pdf':str(PDF),'pages_expected':9,'annual_rows':len(annual_df),'factor_ic_rows':len(ic_df),'baseline_oos_cagr':ob['cagr'],'smart_oos_cagr':os['cagr'],'benchmark_oos_cagr':bm['cagr']},indent=2))


