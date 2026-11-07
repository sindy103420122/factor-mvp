# AI 協作日誌：陳楓和（jojo-panda）

## 紀錄 #1：用 AI 產生 MVP 的規格與程式
- 階段：需求 / 規格 / 架構 / 實作 / 測試
- 使用的工具與模型：Claude（claude.ai，Claude Opus 5.5）
- 我的提示詞：上傳作業規格 PDF 與第 1 週投影片，問「要做甚麼」；選定方向 2 後，請 AI 同時產生規格文件與可執行的程式骨架。
- AI 的回覆重點：產生 US-102～104 三則使用者故事、Gherkin 情境、ADR-001（選管線架構），以及 app/ 的完整管線，可用 `python -m app.runner --demo` 一行指令重現。AI 把它做的假設列在 docs/OPEN_QUESTIONS.md。
- 我的決定：修改後接受。理由：把 AI 的檔案複製進 Repo 後，git status 顯示 AGENTS.md、prompts/、US-101 等 8 個我沒打算修改的檔案也變成 modified。查證後主要是換行符號不同，但也可能覆蓋掉組長改過的內容，所以我用 git restore 還原這 8 個檔案，只保留真正有改的部分。參數部分我逐條看過 OPEN_QUESTIONS.md，決定 MVP 先採用預設值，之後在樣本內做敏感度分析，紀錄在 docs/DECISIONS_jojo-panda.md。

## 紀錄 #2（AI 出錯）：使用了付費資料表
- AI 犯的錯：FinMind 備案程式第一版使用還原股價資料表 TaiwanStockPriceAdj，但它需要付費會員。AI 寫程式時只確認了資料表名稱，沒有確認權限等級。
- 我如何發現：我用自己的免費帳號實際執行下載，股票清單成功後，下載股價時出現錯誤「Your level is register」，程式中斷。
- 如何修正，並新增了哪個情境或測試來防止再犯：改用免費的未還原股價，再以除權息、減資的參考價自行計算還原報酬。新增 2 個 Gherkin 情境：「除息日的報酬以參考價計算」、「減資恢復買賣不視為大漲」，確認除權息造成的股價跳空不會被當成漲跌。修正後成功下載 100 檔並完成真實資料樣本內回測。

## 紀錄 #3（AI 出錯）：.gitignore 漏掉暫存資料夾
- AI 犯的錯：AI 新增 FinMind 下載功能時，會把資料暫存在 data/finmind_cache/，但 .gitignore 只排除了 data/raw/、data/processed/、data/demo/，沒有排除這個新資料夾。
- 我如何發現：commit 前執行 git status，清單裡出現 data/，代表下載的資料會被一起上傳到公開的 Repo。
- 如何修正，並新增了哪個情境或測試來防止再犯：在 .gitignore 加上 data/，排除整個資料夾；之後每次 commit 前都先看 git status，確認沒有資料或金鑰。

## 紀錄 #4（AI 出錯）：PR 送錯到老師的範本 Repo
- AI 犯的錯：AI 教我用 push 後終端機給的網址開 PR，但沒提醒組長的 Repo 是從老師範本 fork 的，GitHub 會預設把 PR 送到上游，結果 PR 送到了 freeman1217/factor-mvp。
- 我如何發現：組長說看到我的請求，但組長 Repo 的 PR 清單只有 #1、#2，沒有我的。我在另一個對話詢問後，比對老師 Repo 的 PR 紀錄，發現第 1 號 PR 就是我的 commit。
- 如何修正，並新增了哪個情境或測試來防止再犯：關閉送錯的 PR，重新開 PR 並確認 base repository 是 sindy103420122/factor-mvp（PR #7）；在 GitHub 網頁上解決 README 衝突，保留組員分工。之後開 PR 一律先檢查 base repository，PR #9 也照這個方式送對。

## 紀錄 #5（AI 出錯）：TEJ 日期解析錯誤
- AI 犯的錯：TEJ 轉檔程式讀取數字型日期（如 20150508）時，若欄位有空值，pandas 會讀成 20150508.0，所有營收公布日都被誤判為缺值。程式不會報錯，只會讓結果默默變保守。
- 我如何發現：這個錯誤是 AI 用模擬的 TEJ 格式檔案自我測試時發現並告訴我的。這讓我學到，只看程式碼看不出資料格式的問題，必須用接近真實的資料實際跑一次。
- 如何修正，並新增了哪個情境或測試來防止再犯：新增 parse_date 統一處理各種日期格式；轉檔時印出「缺公布日、改用替代日」的筆數作為警示。
