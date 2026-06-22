# factors/factor_validation.py
import pandas as pd
import numpy as np
from scipy.stats import spearmanr
from data.data_manager import DataManager

def validate_factor(symbol, factor_name='momentum', lookback=20, forward_periods=[5, 10, 20]):
    dm = DataManager()
    end = pd.Timestamp.now().strftime('%Y%m%d')
    start = (pd.Timestamp.now() - pd.DateOffset(years=3)).strftime('%Y%m%d')
    df = dm.get_stock_data(symbol, start, end)
    if df.empty or len(df) < 252:
        return {"error": "数据不足"}

    close = df['close']

    if factor_name == 'momentum':
        factor_series = close.rolling(lookback).apply(lambda x: x.iloc[-1]/x.iloc[0]-1, raw=False)
    elif factor_name == 'volatility':
        factor_series = -close.pct_change().rolling(lookback).std()
    else:
        return {"error": f"未知因子: {factor_name}"}

    factor_series = factor_series.dropna()
    common_dates = factor_series.index

    ic_results = {}
    group_results = {}

    for period in forward_periods:
        fwd_ret = close.pct_change(period).shift(-period).reindex(common_dates).dropna()
        aligned_factor = factor_series.reindex(fwd_ret.index).dropna()
        fwd_ret = fwd_ret.reindex(aligned_factor.index)

        if len(aligned_factor) < 30:
            ic_results[period] = {"IC": None, "IC_IR": None}
            continue

        ic, _ = spearmanr(aligned_factor, fwd_ret)
        ic_val = round(ic, 4) if not np.isnan(ic) else None
        ic_ir = round(ic / aligned_factor.std(), 4) if ic is not None and aligned_factor.std() != 0 else None

        try:
            n_groups = 5
            labels = [f'Q{i+1}' for i in range(n_groups)]
            groups = pd.qcut(aligned_factor, n_groups, labels=labels, duplicates='drop')
            group_ret = fwd_ret.groupby(groups).mean()
            group_results[period] = group_ret.to_dict() if not group_ret.empty else None
        except ValueError:
            group_results[period] = None

        ic_results[period] = {"IC": ic_val, "IC_IR": ic_ir}

    autocorr = factor_series.autocorr(lag=1)

    return {
        "symbol": symbol,
        "factor": factor_name,
        "lookback": lookback,
        "ic": ic_results,
        "group_returns": group_results,
        "autocorr_1": round(autocorr, 4) if not pd.isna(autocorr) else None
    }