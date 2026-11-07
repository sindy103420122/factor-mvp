import pandas as pd
import numpy as np

def get_mock_data(date: str) -> pd.DataFrame:
    """
    獲取指定日期的台股假資料 (Mock Data)，供 MVP 測試與回測管線使用。
    模擬已解決 Point-in-Time (無前視偏誤) 的當日可用資訊。
    """
    data = {
        'ticker': ['1101', '2330', '2317', '2603', '0000'],
        # US-332 需用資料
        'close_price': [50.0, 100.0, 150.0, 60.0, 10.0],
        'ttm_eps': [-1.5, 5.0, 10.0, 3.0, 1.0],
        'payout_ratio': [0.8, 0.8, 0.5, 0.0, 0.5],
        # US-496 需用資料
        'inst_buy_5d': [0, 5000, 2000, 0, np.nan], 
        'total_shares': [200000, 500000, 1000000, 100000, 50000],
        # US-578 需用資料
        'margin_now': [15.0, 25.0, 10.0, 30.0, 15.0],
        'margin_last': [np.nan, 20.0, 8.0, 40.0, 10.0]
    }
    return pd.DataFrame(data).set_index('ticker')