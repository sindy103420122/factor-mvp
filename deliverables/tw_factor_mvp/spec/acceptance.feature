Feature: 台股月頻因子回測
  Scenario: 用固定資料產生可重現結果
    Given 一份符合資料契約的月末股票面板
    When 執行 baseline 與 smart 回測
    Then 每月輸出持股、成本後報酬和含息基準報酬
    And 匯出樣本內與樣本外摘要

  Scenario: 防止當月未來報酬洩漏到智慧權重
    Given 因子及其下月已實現報酬
    When 計算某訊號月因子權重
    Then 權重只能使用該月之前已觀測到的 IC

  Scenario: 排除無法投資股票
    Given 股票池中有 investable 為 false 的股票
    When 排序並形成組合
    Then 該股票不會出現在持股明細

  Scenario: 輸入資料不符合契約
    Given 缺欄位、重複股票月份或百分比格式報酬
    When 載入資料
    Then 程式明確回報錯誤而不輸出績效

  Scenario: 沒有可投資股票
    Given 當月所有股票皆不可投資
    When 執行當月回測
    Then 輸出零持股與零投資組合報酬並保留基準序列
