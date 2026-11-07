# 台股智慧因子投資策略

用 AI 協作，從需求規格開始，完成一個可重現的台股因子投資專題，並用扣除成本的回測檢驗它。
做法參考 GradeInsight 範例儲存庫：先寫需求，再寫 BDD 情境，最後才讓 AI 依規格實作與測試。

- 樣本內期間：2015/01～2022/12（研發、調參數）
- 樣本外期間：2023/01～2026/09（只用於最終驗收，只跑一次）
- Benchmark：臺灣加權報酬指數（含息）
- 調倉頻率：月調倉
- 專題方向：方向 2，智慧調權重

## 本 Repo 包含兩套成果

| | 主系統（MVP） | 探索版原型 |
|---|---|---|
| 位置 | `app/`、`features/`、`requirements/`、`docs/` | `deliverables/tw_factor_mvp/` |
| 用途 | 第 2 週 MVP 繳交主體，依講義的規格流程完成 | 方向 2「智慧調權重」的提早試作 |
| 因子 | 月營收年增率（成長）、12-1 動能（動能） | 12-1 動能、6-1 動能、近月反轉、低波動、流動性 |
| 選股 | 前 30 檔等權 | baseline 與 IC 加權（Smart）各取前 5 檔 |
| 股票池 | 上市櫃普通股，含已下市櫃，流動性篩選 | 12 檔現存大型股 |
| 測試 | behave，22 個 Gherkin 情境 | unittest |
| 執行 | `python -m app.runner` | 見下方「探索版原型」 |

**請以主系統為 MVP 的評分對象。** 探索版原型是組員為了方向 2 先行試作的版本，限制請見下方說明。

## 快速開始（主系統）

### 1. 建立環境

```bash
python -m venv .venv
.venv\Scripts\activate           # Mac / Linux：source .venv/bin/activate
pip install -r requirements.txt
```

Windows 若啟用 venv 時出現「已停用指令碼執行」，先執行：
`Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass`
若出現中文亂碼，先執行 `chcp 65001`。

### 2. 一行指令重現

```bash
python -m app.runner --demo                     # 用假資料跑完整條管線（任何電腦都能跑，約 10 秒）
python -m app.runner --data data/processed      # 用真實資料跑（資料準備見下方）
python -m app.runner --demo --config configs/jojo-panda.json   # 使用個人參數設定檔
```

結果輸出到 `output/`：`summary.csv`（績效摘要）、`monthly.csv`（每月明細）、`trade_log.csv`（無法成交紀錄）。
假資料結果固定為年化報酬 10.30%、Sharpe 0.67，可用來確認環境與可重現性。

### 3. 執行測試

```bash
behave
```

目前 5 個 Feature、22 個情境全部通過，執行輸出附在 `docs/behave_output.txt`。

## 資料來源

| 來源 | 指令 | 說明 |
|---|---|---|
| TEJ（主要） | `python -m app.tej_convert` | 需學校授權，匯出方式見 `docs/DATA_TEJ.md` |
| FinMind（備案） | `python -m app.finmind_download --limit 100` | 免費帳號即可，說明見 `docs/DATA_FINMIND.md` |

FinMind 備案只使用免費資料表：以未還原股價搭配除權息、減資參考價自行計算還原報酬；月營收沒有實際公布日，一律以次月 10 日作為可用日。
token 請設定在環境變數 `FINMIND_TOKEN`，不要寫進程式或 commit。
資料有授權限制，`data/` 與 `output/` 都已列入 `.gitignore`，不上傳。

## 目前進度（第 2 週 MVP）

| 驗收項目 | 狀態 | 位置 |
|---|---|---|
| User Story 至少 3 則 | 完成，4 則 | `requirements/US-101`～`US-104` |
| Gherkin 至少 3 個 Feature、6 個情境 | 完成，5 個 Feature、22 個情境 | `features/*.feature` |
| 架構決策紀錄 | 完成，管線架構 | `docs/ADR-001_architecture.md` |
| AGENTS.md 與三支提示詞 | 完成 | `AGENTS.md`、`prompts/` |
| 至少 2 個因子、2 個類別 | 完成：月營收年增率、12-1 動能 | `app/factors.py` |
| 規則式 baseline、月調倉、扣成本、換手率 | 完成 | `app/portfolio.py`、`app/backtest.py` |
| behave 全部通過並附輸出 | 完成 | `docs/behave_output.txt` |
| AI 協作日誌至少 3 筆 | 完成，5 筆，其中 4 筆 AI 出錯 | `ai_log/` |

### 真實資料樣本內回測（FinMind，抽樣 100 檔，2015～2022）

| 指標 | 策略 | Benchmark |
|---|---|---|
| 年化報酬（扣成本） | 3.40% | 10.46% |
| 年化波動 | 25.02% | |
| Sharpe（rf=0） | 0.14 | |
| 最大回撤（月頻） | -30.23% | |
| 平均月換手率 | 14.69% | |
| 平均持股檔數 | 25.78 | |

抽樣股票數較少，部分月份可選股票不足 30 檔，因此這份結果主要用來驗證流程能以真實資料跑通。
下一步會擴大到 500 檔以上再評估。

## 參數設定

預設參數在 `app/config.py`。每位組員可在 `configs/<GitHub 帳號>.json` 放自己的參數，只寫要改的項目，
決策理由寫在 `docs/DECISIONS_<GitHub 帳號>.md`。目前預設值：

- 流動性門檻：過去 60 日平均成交金額 2,000 萬元
- 持股：前 30 檔等權
- 成本：手續費 0.1425%、證交稅 0.3%（賣出）、滑價單邊 0.1%

## 目錄

```
AGENTS.md          給 AI 的規則（先讀這份）
requirements/      User Story，一則一個檔
features/          Gherkin 情境（.feature）
features/steps/    behave 步驟定義
prompts/           三支可重用的提示詞
docs/              ADR、資料說明、規格不確定點、方向 2 計畫
configs/           個人參數設定檔
app/               主系統程式碼
ai_log/            AI 協作日誌
deliverables/      探索版原型
MVP_CHECKLIST.md   MVP 驗收清單
```

## 探索版原型（deliverables/tw_factor_mvp/）

```bash
pip install -r deliverables/tw_factor_mvp/requirements.txt
cd deliverables/tw_factor_mvp
python -m unittest discover -s tests -v
python src/build_panel.py
python src/backtest.py --panel data/panel.csv --out reports/run --top-n 5 --fee-bps 14.25 --tax-bps 30 --slippage-bps 10
python src/create_report.py
```

已知限制，誠實揭露如下：

- 股票池只有 12 檔現存大型股，有存活者與選樣偏誤，不代表全市場績效。
- 這份原型**已經執行過樣本外期間（2023～2026/09）**，早於規劃的第 7 週驗收。
  全組決議：主系統的參數與方法**不參考**這份樣本外結果；第 7 週主系統仍只執行一次樣本外驗收。

## 規則重點

- 因子只能使用計算日當天以前已公布的資料。
- 不隨機切分時間序列；回測一律扣成本；樣本外不用於調參。
- 程式碼只放 `app/`，根目錄不放 `.py`。
- 樣本外（2023-01 起）預設鎖住，`app/config.py` 的 `unlock_oos` 只在第 7 週驗收時改成 True。
- 資料與金鑰不 commit。開 PR 前確認 base repository 是本 Repo，不是老師的範本。

## 組員分工

| 姓名 | 負責任務 |
| 陳心怡 |專案進度與 GitHub Repo 管理、整合各組員成果、審查 Pull Request|
| 陳哲諺 | 協助策略績效分析、回測結果整理與報告文件撰寫 |
| 鄭稟哲 | 需求整理與功能規劃 |
| 陳楓和 | MVP 主系統管線、Gherkin 測試、ADR、FinMind 資料來源 |
| 王士哲 | 檢查錯誤 |
| 李承祐 | README 與使用說明整理、成果簡報 |
