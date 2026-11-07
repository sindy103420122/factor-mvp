Feature: US-332 預估高股息殖利率因子
  As a 量化投資人
  I want 系統能以 TTM EPS 與宣告配息率計算預估殖利率
  So that 我能提前佈局具備高殖利率潛力的價值型標的

  Scenario: 成功計算正常的預估殖利率
    Given 某檔股票的 TTM EPS 為 5.0
    And 預估配息率固定為 0.8
    And 計算日當天的最新收盤價為 100.0
    When 系統計算預估殖利率
    Then 預估殖利率結果應為 0.04

  Scenario: 異常情境_TTM EPS為負值時直接淘汰
    Given 某檔股票的 TTM EPS 為 -1.5
    And 預估配息率固定為 0.8
    And 計算日當天的最新收盤價為 50.0
    When 系統計算預估殖利率
    Then 預估殖利率結果應直接標記為 0.0

  Scenario: 邊界情境_歷史配息率為0時直接淘汰
    Given 某檔股票的 TTM EPS 為 3.0
    And 預估配息率固定為 0.0
    And 計算日當天的最新收盤價為 60.0
    When 系統計算預估殖利率
    Then 預估殖利率結果應直接標記為 0.0