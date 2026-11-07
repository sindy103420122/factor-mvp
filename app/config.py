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


def load_settings(path: str = None) -> Settings:
    """讀取個人設定檔（JSON），只覆蓋檔案裡有寫的參數，其餘用預設值。

    個人設定檔放在 configs/，例如 configs/jojo-panda.json。
    寫錯參數名稱會直接報錯，避免打錯字卻默默用了預設值。
    """
    import json
    from dataclasses import fields

    settings = Settings()
    if path is None:
        return settings
    with open(path, encoding="utf-8") as f:
        raw = json.load(f)
    raw = {k: v for k, v in raw.items() if not k.startswith("_")}   # _ 開頭的欄位是註解

    cost_raw = raw.pop("cost", {})
    valid = {f.name for f in fields(Settings)} - {"cost"}
    unknown = set(raw) - valid
    if unknown:
        raise KeyError(f"設定檔 {path} 有不認得的參數：{sorted(unknown)}。可用的參數：{sorted(valid)}")
    for k, v in raw.items():
        setattr(settings, k, tuple(v) if k == "factors" else v)

    cost_valid = {f.name for f in fields(CostConfig)}
    unknown = set(k for k in cost_raw if not k.startswith("_")) - cost_valid
    if unknown:
        raise KeyError(f"設定檔 {path} 的 cost 有不認得的參數：{sorted(unknown)}。可用的參數：{sorted(cost_valid)}")
    for k, v in cost_raw.items():
        if not k.startswith("_"):
            setattr(settings.cost, k, v)
    return settings


def describe(settings: Settings) -> str:
    """把目前使用的參數印出來，方便確認與截圖。"""
    c = settings.cost
    return "\n".join([
        f"期間：{settings.start} ~ {settings.end}（樣本外鎖：{'已解鎖' if settings.unlock_oos else '鎖住'}）",
        f"流動性門檻：過去 {settings.liquidity_lookback} 日平均成交金額 {settings.min_avg_value:,.0f} 元",
        f"持股：前 {settings.top_n} 檔等權",
        f"因子權重：{settings.factor_weights}",
        f"成本：手續費 {c.fee_rate:.4%}、證交稅 {c.tax_rate:.2%}、滑價 {c.slippage:.2%}",
    ])


class OutOfSampleLockedError(RuntimeError):
    """樣本外期間尚未解鎖時拋出。"""


def check_period(end: str, settings: Settings) -> None:
    """對應 Scenario: 樣本外期間預設鎖住。"""
    import pandas as pd
    if pd.Timestamp(end) >= pd.Timestamp(settings.oos_start) and not settings.unlock_oos:
        raise OutOfSampleLockedError(
            f"樣本外期間（{settings.oos_start} 起）尚未解鎖。"
            "樣本外只能在最終驗收時執行一次，請確認後再設定 unlock_oos=True。")
