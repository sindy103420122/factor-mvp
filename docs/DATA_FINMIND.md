# 備案資料來源：FinMind（不需要 TEJ）

TEJ 無法使用時的替代方案。FinMind 是免費的台股資料 API，涵蓋本專題 MVP 需要的四種資料。

## 一行指令

```powershell
python -m app.finmind_download --limit 300     # 先抽 300 檔試跑
python -m app.runner --data data/processed     # 用下載的真實資料回測
```

拿掉 `--limit 300` 就是全部上市櫃普通股（含已下市櫃）。

## 下載前準備：免費 token（建議）

1. 到 FinMind 官網免費註冊，登入後在個人頁面複製 API token。
2. 在 PowerShell 設定環境變數（只對目前視窗有效）：
   ```powershell
   $env:FINMIND_TOKEN = "貼上你的token"
   ```
3. token 是個人密碼，**不要寫進程式、不要 commit、不要貼給別人**（包括 AI）。

沒有 token 也能跑，但每小時的下載次數較少。

## 下載的資料與對應

| FinMind 資料表 | 用途 | 轉成 |
|---|---|---|
| TaiwanStockInfo | 現有上市櫃股票清單 | 股票池 |
| TaiwanStockDelisting | 已下市櫃清單 | 避免存活者偏誤 |
| TaiwanStockPrice | 未還原股價、成交金額 | prices.csv（自行還原） |
| TaiwanStockDividendResult | 除權息前收盤價與參考價 | 計算還原報酬 |
| TaiwanStockCapitalReductionReferencePrice | 減資前收盤價與恢復買賣參考價 | 計算還原報酬 |
| TaiwanStockMonthRevenue | 月營收 | revenue.csv |
| TaiwanStockTotalReturnIndex（TAIEX） | 加權報酬指數（含息） | benchmark.csv |

## 為什麼不用 FinMind 的還原股價

FinMind 的還原股價（TaiwanStockPriceAdj）需要付費會員。本專題改用免費的未還原股價，
再用除權息、減資的參考價自行還原：事件當天的報酬 = 今日收盤 ÷ 昨日收盤 × (事件前收盤 ÷ 參考價) − 1，
其餘交易日照常計算。這與付費還原股價的原理相同，並已寫成 Gherkin 情境測試。

若免費會員也無法取得加權報酬指數，程式會改用加權指數（不含息）並印出警告，
此時 benchmark 會被低估，報告中必須說明。

## 下載時間

免費會員每檔股票最多需要 4 次請求（股價、營收、除權息、減資）。全部約 1,900 多檔，依 FinMind 當時的次數上限，可能需要數小時。
程式會把每檔存成快取（`data/finmind_cache/`），**中斷後重新執行同一個指令會從中斷處繼續**，
遇到次數上限會自動等待重試。建議先用 `--limit 300` 確認流程，再挑一個晚上跑全部。

## 與 TEJ 相比的限制（報告中要說明）

| 項目 | FinMind 的處理 | 影響 |
|---|---|---|
| 月營收公布日 | 官方資料沒有實際公告日，一律用**次月 10 日**（法定期限） | 較保守：部分公司較早公布，訊號會晚幾天才用到 |
| 上市日 | 用下載資料中第一筆股價日期近似 | 對 2015 年後的回測影響很小 |
| 下市櫃 | 下市日後 30 天內仍有股價的，視為轉板而非下市 | 已寫成 Gherkin 情境測試 |
| 漲停 | 以還原股價日報酬 ≥ 9.5%（2015/6 前 6.5%）近似 | 除權息日前後可能誤判 |
| 普通股 | 4 位數代碼、不以 0 開頭 | 少數特殊代碼可能誤判 |
| 抽樣（若使用 `--limit`） | 固定亂數種子 42，可重現 | 報告要寫明是抽樣結果 |

## 授權

FinMind 資料一樣**不要 commit**（`data/` 已在 `.gitignore`）。README 要寫清楚下載指令與下載日期，讓別人可以重現。
