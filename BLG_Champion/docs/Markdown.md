# 台股智慧因子投資策略 (Factor MVP)

本專案為台股量化選股管線的最小可行性產品 (MVP)，具備資料抓取 (Mock)、因子計算、投資組合權重分配與單期回測功能。
開發過程嚴格遵循 BDD (行為驅動開發) 規範，透過 Gherkin 情境確保規格與程式碼一致。

## 環境建置 (Windows)
請在終端機 (PowerShell 或 cmd) 執行以下指令建立虛擬環境並安裝套件：
```powershell
# 1. 建立虛擬環境
python -m venv .venv

# 2. 啟動虛擬環境 (cmd 模式)
.venv\Scripts\activate.bat
# 若在 PowerShell 模式，請輸入： .\.venv\Scripts\Activate.ps1

# 3. 安裝必要套件
pip install -r requirements.txt