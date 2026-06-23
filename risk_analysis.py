# factors/risk_analysis.py
import pandas as pd
import numpy as np
from data.data_manager import DataManager

def risk_analysis(symbol):
    dm = DataManager()
    end = pd.Timestamp.now().strftime('%Y%m%d')
    start = (pd.Timestamp.now() - pd.DateOffset(years=5)).strftime('%Y%m%d')
    df = dm.get_stock_data(symbol, start, end)
    if df.empty or len(df) < 500:
        return {"error": "历史数据不足"}

    returns = df['close'].pct_change().dropna()
    latest_price = float(df['close'].iloc[-1])

    var_95 = np.percentile(returns, 5)
    var_99 = np.percentile(returns, 1)
    cvar_95 = returns[returns <= var_95].mean()
    cvar_99 = returns[returns <= var_99].mean()

    periods = [5, 10, 20, 60]
    vol_cone = {}
    for p in periods:
        vol = returns.rolling(p).std() * np.sqrt(252)
        vol = vol.fillna(0)
        vol_cone[f"{p}日"] = {
            "min": round(float(vol.min()), 4),
            "median": round(float(vol.median()), 4),
            "max": round(float(vol.max()), 4),
            "current": round(float(vol.iloc[-1]), 4)
        }

    cummax = df['close'].cummax()
    drawdown = (df['close'] - cummax) / cummax
    max_dd = drawdown.min()
    max_dd_date = drawdown.idxmin()
    recovery = df['close'][max_dd_date:].ge(cummax[max_dd_date])
    if recovery.any():
        recovery_date = recovery[recovery].index[0]
        recovery_days = (recovery_date - max_dd_date).days
    else:
        recovery_days = None

    return {
        "symbol": symbol,
        "latest_price": latest_price,
        "VaR_95%": round(float(var_95), 4) if not np.isnan(var_95) else None,
        "CVaR_95%": round(float(cvar_95), 4) if not np.isnan(cvar_95) else None,
        "VaR_99%": round(float(var_99), 4) if not np.isnan(var_99) else None,
        "CVaR_99%": round(float(cvar_99), 4) if not np.isnan(cvar_99) else None,
        "volatility_cone": vol_cone,
        "max_drawdown": round(float(max_dd), 4) if not pd.isna(max_dd) else None,
        "max_drawdown_date": max_dd_date.strftime('%Y-%m-%d'),
        "recovery_days": recovery_days
    }