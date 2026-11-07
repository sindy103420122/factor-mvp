# 台股智慧因子選股系統 (Factor MVP)

本專案為一個模組化的台股量化選股與單期回測系統 (Factor MVP)。專案開發過程嚴格遵循 **BDD (行為驅動開發)** 規範，透過 Gherkin 情境規格書確保業務邏輯與程式碼的一致性，並支援自動化測試、績效模擬以及視覺化圖表產出。

---

## 🏗️ 專案架構與模組設計 (ADR-001)

本系統依循清晰的管線設計（Pipeline Design），各階段職責分明：

```text
Data (資料載入) ──> Factors (因子計算) ──> Portfolio (權重配置) ──> Backtest (回測模擬) ──> Report & Docs (成果與圖表)
```

- **`app/data.py`**：處理 Point-in-Time 截面資料載入與防前視偏誤（Point-in-Time Correctness）。
- **`app/factors.py`**：核心因子運算，包含：
  - **US-332**：預估高股息殖利率因子 $\frac{\text{TTM EPS} \times \text{Payout Ratio}}{\text{Close Price}}$
  - **US-496**：投信買超佔股本比因子 $\frac{\text{5-Day Inst Buy}}{\text{Total Shares}}$
  - **US-578**：單季毛利率年變動因子 $\text{Margin}_{\text{now}} - \text{Margin}_{\text{last}}$
- **`app/portfolio.py`**：進行橫斷面 Z-score 標準化並分配投資組合權重。
- **`app/backtest.py`**：執行單期回測，計算原始報酬、交易成本與淨報酬。
- **`app/runner.py`**：系統指揮中心，串接完整管線並自動產出 `docs/` 視覺化圖表。

---

## 🛠️ 環境建置與安裝 (Windows / PowerShell)

請確保您的電腦已安裝 Python 3.8+，並在專案根目錄下依序執行以下指令：

### 1. 建立並啟動虛擬環境 (.venv)
```powershell
# 建立虛擬環境
python -m venv .venv

# 啟動虛擬環境 (PowerShell)
.\.venv\Scripts\Activate.ps1
# 備用 (若 PowerShell 遭遇指令碼限制，可切換至 cmd 執行)：
# cmd
# .venv\Scripts\activate.bat
```

### 2. 安裝必要套件
```powershell
pip install -r requirements.txt
```

---

## 🧪 執行自動化測試 (BDD)

本專案透過 `behave` 執行行為驅動開發測試，驗證 3 個 User Story 共 8 個驗收情境：

```powershell
behave
```
*當看見終端機顯示 `3 features passed, 0 failed`，即代表所有業務邏輯與因子計算完全符合規格！*

---

## 📈 執行回測管線與視覺化圖表

確認測試通過後，即可執行主程式來產出單期回測績效報告以及高解析度圖表：

```powershell
python app/runner.py
```

執行後將在終端機輸出績效結算，並自動於 **`docs/`** 資料夾產生以下圖表：
1. **`factor_comparison.png`**：橫斷面因子特徵比較柱狀圖
2. **`portfolio_pie.png`**：目標投資組合權重配置圓餅圖

---

## 👥 AI 協作聲明
本專案開發過程參考 `ai_log/AI IAA.md` 紀錄，透過與 AI 協同規劃架構、除錯（如解決 `ModuleNotFoundError` 與路徑相依問題）與圖表擴充，實現高效且高品質的交付物產出。