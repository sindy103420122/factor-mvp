"""全部可調參數集中在這裡。改參數 = 改這個檔案，並在 ai_log 或 README 記錄原因。"""
from dataclasses import dataclass, field


@dataclass
class CostConfig:
    fee_rate: float = 0.001425   # 手續費，買賣各一次，不打折
    tax_rate: float = 0.003      # 證交稅，只在賣出時課徵
    slippage: float = 0.001      # 滑價，單邊 0.1%（自訂假設，需在報告說明）


@dataclass
class Settings:
    # 期間
    start: str = "2015-01-01"
    end: str = "2022-12-31"
    oos_start: str = "2023-01-01"     # 樣本外起點
    unlock_oos: bool = False          # 第 7 週驗收時才改成 True，且只跑一次

    # 股票池（US-103）
    min_avg_value: float = 20_000_000  # 過去 60 日平均成交金額門檻（元）
    liquidity_lookback: int = 60

    # 選股（US-104 baseline）
    top_n: int = 30
    factors: tuple = ("revenue_yoy", "momentum_12_1")
    # baseline：等權合成。方向 2 的智慧方法會在第 6～7 週替換這裡的權重來源
    factor_weights: dict = field(default_factory=lambda: {
        "revenue_yoy": 0.5, "momentum_12_1": 0.5})

    cost: CostConfig = field(default_factory=CostConfig)


class OutOfSampleLockedError(RuntimeError):
    """樣本外期間尚未解鎖時拋出。"""


def check_period(end: str, settings: Settings) -> None:
    """對應 Scenario: 樣本外期間預設鎖住。"""
    import pandas as pd
    if pd.Timestamp(end) >= pd.Timestamp(settings.oos_start) and not settings.unlock_oos:
        raise OutOfSampleLockedError(
            f"樣本外期間（{settings.oos_start} 起）尚未解鎖。"
            "樣本外只能在最終驗收時執行一次，請確認後再設定 unlock_oos=True。")
