AI 協作日誌
紀錄 #1
階段：架構與實作

使用的工具與模型：Gemini AI 協作者、VS Code、Python (pandas, numpy)

我的提示詞（關鍵片段）：

「請根據 features/*.feature 的所有情境，在 app/ 實作最小可行（MVP）的台股因子管線，並同步生成自動化測試。架構依循 Data → Factors → Portfolio → Backtest → Report。」

AI 的回覆重點：

規劃了符合 ADR-001 規範的 4 階段模組化管線（data.py, factors.py, portfolio.py, backtest.py, runner.py）。

將 3 個核心 User Story（US-332 殖利率、US-496 投信買超、US-578 毛利率年變動）轉化為標準的 pandas 計算邏輯。

我的決定：接受。理由：模組職責劃分明確，且完美對應 BDD 規格書的驗收情境。

紀錄 #2（AI 出錯的案例）
AI 犯的錯：

檔名對應與模組匯入錯誤：AI 在提供測試步驟（stock_steps.py）與因子模組時，假設了標準無前綴的檔名（如 factors.py），而使用者本地端專案因協作或備份習慣加上了 BLG_ 前綴（如 BLG_factors.py）。這導致 behave 執行時發生 ModuleNotFoundError: No module named 'app.factors'。

幽靈檔案干擾：測試步驟檔中殘留了未在管線內實作的 revenue_yoy 函式匯入，導致 ImportError。

我如何發現：

在終端機執行 behave 自動化測試時，連續遭遇 Python 報出 ModuleNotFoundError 與 ImportError: cannot import name 'revenue_yoy' 的紅字崩潰。

如何修正，並新增了哪個情境或測試來防止再犯：

修正方式：統一將所有模組與資料夾的 BLG_ 前綴移除，還原為標準的 app/factors.py 與 app/data.py 架構；刪除干擾的 revenue_steps.py 幽靈檔案；並在測試檔開頭補上 sys.path.insert(0, ...) 動態路徑導向。

防範措施：在專案根目錄的 README.md 中新增了「模組命名與目錄結構規範」說明，確保後續擴充因子時，檔案命名與 import 路徑嚴格保持一致。

紀錄 #3
階段：測試與產出報告

使用的工具與模型：Gemini AI 協作者、Matplotlib、VS Code Terminal

我的提示詞（關鍵片段）：

「除了這個以外還有其他可生成的圖或表格嗎?」

AI 的回覆重點：

建議並提供基於 matplotlib 的視覺化擴充程式碼。

自動生成並儲存兩張高解析度圖表至 docs/ 資料夾：

factor_comparison.png：橫斷面因子特徵比較柱狀圖。

portfolio_pie.png：選股投資組合權重配置圓餅圖。

我的決定：接受。理由：將抽象的文字回測結果轉化為直觀的視覺圖表，大幅提升了期末專題交付物與書面報告的專業度與說服力。
