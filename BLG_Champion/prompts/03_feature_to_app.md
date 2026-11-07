# 提示詞 3：情境轉程式與自動測試

## 任務目標
請根據 `features/*.feature` 的所有情境，在 `app/` 實作最小可行（MVP）的台股因子管線，並同步生成自動化測試。

## 規範
- 邏輯依據：嚴格遵循 `features/*.feature` 與 `AGENTS.md`，功能 100% 來自規格。
- 架構：管線架構 data → factors → portfolio → backtest → report，參考 `docs/ADR-001_architecture.md`。
- 程式碼只放在 `app/`；測試步驟放在 `features/steps/`，使用 behave。
- 關鍵邏輯加上繁體中文註解，並標明對應的 Scenario。

## 交付物
- 完整的系統程式碼（app/）
- 完整的測試程式碼（features/steps/）
- requirements.txt
- README.md：說明如何建立 venv、如何執行、如何執行 `behave` 並解讀結果

## 先問再做
先列出你的假設與待確認問題，我回覆後再開始寫程式。
不要一次產出全部：依序產出 資料與因子 → 組合與回測 → 報告 → 測試。
