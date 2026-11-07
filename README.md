# 台股智慧因子投資策略：MVP 鷹架

做法參考 GradeInsight 範例儲存庫：先寫需求，再寫 BDD 情境，最後才讓 AI 依規格實作與測試。

## 目錄
```
AGENTS.md          給 AI 的規則（先讀這份）
requirements/      User Story，一則一個檔
features/          Gherkin 情境（.feature）
features/steps/    behave 步驟定義
prompts/           三支可重用的提示詞
docs/              架構決策紀錄（ADR）
app/               所有系統程式碼只放這裡
ai_log/            AI 協作日誌
MVP_CHECKLIST.md   下週繳交的驗收清單
```

## 工作順序
1. 複製 `requirements/US-000_TEMPLATE.md`，寫 3 則故事（參考 US-101）。
2. 用 `prompts/01_refine_story.md` 請 AI 檢視故事，你決定接受、修改或拒絕。
3. 用 `prompts/02_story_to_feature.md` 把故事轉成 `.feature`。
4. 完成 `docs/ADR-001_architecture.md`。
5. 用 `prompts/03_feature_to_app.md` 請 AI 在 `app/` 實作並產生測試。
6. 跑 `behave`，對照 `MVP_CHECKLIST.md`，補寫 `ai_log/`。

## 一行指令重現

```bash
python -m app.runner --demo     # 用假資料跑完整條管線（任何電腦都能跑，約 10 秒）
python -m app.runner            # 用 data/processed/ 的 TEJ 資料跑（準備方式見 docs/DATA_TEJ.md）
```
結果輸出到 `output/`：`summary.csv`（績效摘要）、`monthly.csv`（每月明細）、`trade_log.csv`（無法成交紀錄）。

## 目前進度（MVP）
| 項目 | 檔案 |
|---|---|
| 使用者故事 4 則 | `requirements/US-101`～`US-104` |
| Gherkin 4 個 Feature、16 個情境 | `features/*.feature` |
| 架構決策 | `docs/ADR-001_architecture.md` |
| 因子 2 個（成長、動能） | `app/factors.py` |
| baseline：前 30 檔等權、月調倉、扣成本 | `app/portfolio.py`、`app/backtest.py` |
| 規格不確定點 | `docs/OPEN_QUESTIONS.md` |
| 專題方向 2 草案 | `docs/PLAN_direction2.md` |

## 環境與測試
```bash
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
behave                           # 執行所有情境（目前 16 個）
```
Windows 若出現中文亂碼，先執行 `chcp 65001`。
範例（US-101 月營收年增率）已可通過 3 個情境，請用它確認環境正常，再開始寫你自己的。

## 規則重點
- 因子只能使用計算日當天以前已公布的資料。
- 不隨機切分時間序列；回測一律扣成本；樣本外不用於調參。
- 程式碼只放 `app/`，根目錄不放 `.py`。
- 樣本外（2023-01 起）預設鎖住，`app/config.py` 的 `unlock_oos` 只在第 7 週驗收時改成 True。
- TEJ 原始資料有授權限制，不 commit（見 `.gitignore`）。

## 組員分工

- 姓名：陳哲諺
- 負責任務：協助需求文件整理與測試
- 姓名:王士哲
- 姓名：陳楓和 d1339683
- 姓名：李承祐
- 負責任務：()

