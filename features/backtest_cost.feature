Feature: 回測扣除交易成本並報告換手率
  對應 requirements/US-104_monthly_backtest_with_cost.md

  Background:
    Given 手續費率 0.1425%，證交稅率 0.3%，滑價率 0%

  Scenario: 買進只扣手續費
    When 回測引擎買進 1,000,000 元股票
    Then 該筆交易成本為 1,425 元

  Scenario: 賣出另扣證交稅
    When 回測引擎賣出 1,000,000 元股票
    Then 該筆交易成本為 4,425 元

  Scenario: 全部換股的換手率為 100%
    Given 調倉前持有 "A" 50%、"B" 50%
    When 調倉目標為 "C" 50%、"D" 50%
    Then 本期換手率為 100%

  Scenario: 持股不變時換手率為 0 且不產生成本
    Given 調倉前持有 "A" 50%、"B" 50%
    When 調倉目標為 "A" 50%、"B" 50%
    Then 本期換手率為 0%
    And 本期交易成本為 0 元

  Scenario: 成交日漲停的股票不得新買進
    Given 調倉前持有 "A" 50%、"B" 50%
    And 股票 "C" 在成交日漲停
    When 調倉目標為 "A" 50%、"C" 50%
    Then 股票 "C" 的成交後權重為 0%
    And 股票 "C" 被記錄為 "漲停無法買進"

  Scenario: 樣本外期間預設鎖住
    Given 樣本外期間從 "2023-01-01" 開始且尚未解鎖
    When 研究員要求回測到 "2023-06-30"
    Then 系統拒絕執行並提示樣本外尚未解鎖
