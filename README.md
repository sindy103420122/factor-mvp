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

## 環境與測試
```bash
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
behave                           # 執行所有情境
```
範例（US-101 月營收年增率）已可通過 3 個情境，請用它確認環境正常，再開始寫你自己的。

## 規則重點
- 因子只能使用計算日當天以前已公布的資料。
- 不隨機切分時間序列；回測一律扣成本；樣本外不用於調參。
- 程式碼只放 `app/`，根目錄不放 `.py`。

D1381620鄭稟哲