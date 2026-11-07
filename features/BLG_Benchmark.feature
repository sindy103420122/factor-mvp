Feature: 基準績效 (Benchmark) 對齊與比較

  Scenario: 必須使用含息的加權報酬指數作為比較基準
    Given 系統準備繪製績效對比圖表並計算超額報酬 (Alpha)
    When 系統載入 Benchmark 市場大盤資料
    Then 系統讀取的必須是「臺灣加權股價報酬指數 (含息, TAIEX Total Return Index)」
    And 系統不得使用未包含股息蒸發的普通「臺灣加權指數 (TAIEX)」以免低估大盤績效