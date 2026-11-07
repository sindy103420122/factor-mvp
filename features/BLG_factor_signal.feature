Feature: 多因子合成與缺值處理

  Scenario: 缺少單一因子的股票不會被剔除，並以中性(0)計算
    Given 有一份包含股票 A (資料完整) 與股票 B (缺少殖利率因子) 的資料集
    When 系統以預設權重執行 generate_signals
    Then 股票 A 必須獲得有效的分數
    And 股票 B 也必須獲得有效分數，不應被剔除為 NaN
