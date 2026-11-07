# 台股智慧因子投資 MVP

依簡報規格建置月頻回測流程，並以已取得的公開資料完成一份**探索性樣本報告**。這份結果不代表全市場無偏績效，也不是投資建議。

## 執行

需要 Python 3.11+、pandas、numpy、reportlab。

```powershell
pip install -r requirements.txt
python -m unittest discover -s tests -v
python src/build_panel.py
python src/backtest.py --panel data/panel.csv --out reports/run --top-n 5 --fee-bps 14.25 --tax-bps 30 --slippage-bps 10
python src/create_report.py
```

報告輸出為 `reports/台股智慧因子回測報告.pdf`，可編輯文字版為 `reports/backtest_report.md`。年度報酬、績效、IC 與持倉頻率表格也會輸出到 `reports/`。

## 資料與樣本

FinMind 公開 API 提供 12 檔現存大型股的日價、財報、資產負債表、月營收、股利及除權息結果；TWSE 提供 2015/01–2026/09 的 TAIEX 總報酬指數。原始 CSV、來源、資料列數與 SHA-256 在 `data/raw/manifest.json`。重新抓取可執行 `python src/download_public_data.py`。

股票池固定為 2330、2317、2454、2308、2881、2882、2886、2891、2303、3711、6505、2412。由於是目前存續的大型股回看歷史，存在存活者/選樣偏誤；不可把回測結果解讀為全市場績效。

## 五因子與方法

因子只有價格與流動性訊號：12-1 動能、6-1 動能、近月反轉、252 日低波動、60 日流動性。涵蓋動能、反轉、防禦、流動性四類。價值/品質因子沒有納入，因現有財報缺歷史公告時點及修訂版本。

Baseline 對五因子月內 z-score 等權；Smart 使用最多 36 個月非負平均 Rank IC 權重，至少 12 個有效月前維持等權。每月持有前 5 檔等權。開發期 2016/01–2022/12（84 個月），固定樣本外 2023/01–2026/09（45 個月）；2015 年作動能暖機。

成本假設：佣金每側 14.25 bps、賣出證交稅 30 bps、滑價每側 10 bps。實際券商折扣、停牌、漲跌停、容量與市場衝擊未充分建模。個股除權息用官方參考價比率自建近似還原，並非正式供應商還原價格；基準與股票持有期的月初定價點有輕微差異。

## 結果解讀

樣本外 Baseline CAGR 48.5%，Smart 45.6%，TAIEX 含息 42.5%；策略 Sharpe 低於基準，最大回撤更深。開發期 Baseline CAGR 11.3% 低於基準 12.1%，Smart 為 3.9%。因此不建議直接用於真實資金；報告結論是小樣本探索，須用含下市股的點時股票池與公告日財報重新驗收。

FinMind 免費方案標示限非商業用途；使用或散布原始資料前須遵守來源授權。
