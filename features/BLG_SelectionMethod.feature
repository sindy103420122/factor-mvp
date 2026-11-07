Feature: 選股方法與 Baseline 對照組生成

  Scenario: 系統必須同時產出智慧方法與對照組的投資組合
    Given 系統擁有每月的有效股票池與因子分數
    When 系統執行選股模組 (portfolio.py)
    Then 系統必須能產出一組依據「智慧多因子邏輯」挑選的目標組合
    And 系統也必須能產出一組「Baseline 基準對照組」(例如全市場等權重或大盤市值加權) 供後續績效比較