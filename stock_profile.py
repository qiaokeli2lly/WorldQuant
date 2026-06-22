# features/stock_profile.py
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from data.data_manager import DataManager
from data.index_data import get_index_data
from factors.price_factors import (
    calc_momentum, calc_volatility, calc_rsi, calc_macd,
    calc_kdj, calc_bollinger, calc_volume_ratio, calc_atr
)
from intelligence.data_sources import get_moneyflow

def get_stock_profile(symbol: str, date: str = None) -> dict:
    if date is not None:
        try:
            pd.to_datetime(date)
        except Exception:
            date = None
    if date is None:
        date = datetime.now().strftime('%Y%m%d')

    start = (pd.to_datetime(date) - timedelta(days=200)).strftime('%Y%m%d')
    dm = DataManager()

    df = dm.get_stock_data(symbol, start, date)
    if df.empty:
        return {"error": "行情数据获取失败"}

    fund = dm.get_fundamental(symbol) or {}

    close = df['close']
    high = df['high']
    low = df['low']
    volume = df['volume']

    # 基准指数（A 股用沪深300，美股跳过）
    if dm._is_us_stock(symbol):
        close_index = None
    else:
        df_index = get_index_data('000300.SH', start, date)
        close_index = df_index['close'] if not df_index.empty else None

    # ---- 趋势特征 ----
    mom_20 = calc_momentum(close, 20)
    mom_60 = calc_momentum(close, 60)
    ma_5 = close.rolling(5).mean().iloc[-1]
    ma_20 = close.rolling(20).mean().iloc[-1]
    ma_60 = close.rolling(60).mean().iloc[-1] if len(close) >= 60 else np.nan
    if pd.isna(ma_60):
        ma_arr = "数据不足"
    elif ma_5 > ma_20 > ma_60:
        ma_arr = "多头排列"
    elif ma_5 < ma_20 < ma_60:
        ma_arr = "空头排列"
    else:
        ma_arr = "交叉震荡"

    high_60d = high.tail(60).max() if len(high) >= 60 else high.max()
    low_60d = low.tail(60).min() if len(low) >= 60 else low.min()
    near_high = close.iloc[-1] > high_60d * 0.95
    near_low = close.iloc[-1] < low_60d * 1.05

    # ---- 波动特征 ----
    vol_20 = calc_volatility(close, 20)
    vol_20_abs = abs(vol_20) if not pd.isna(vol_20) else np.nan
    hist_vol = close.pct_change().rolling(20).std()
    vol_percentile = (vol_20_abs < hist_vol).mean() if not hist_vol.empty else np.nan

    upper, lower, mid = calc_bollinger(close)
    bb_width = (upper - lower) / mid if (upper is not None and not pd.isna(upper) and not pd.isna(lower) and not pd.isna(mid)) else np.nan
    atr_val = calc_atr(high, low, close, 14)

    # ---- 量价特征 ----
    vol_ratio_5 = calc_volume_ratio(volume, 5)
    vol_ratio_20 = calc_volume_ratio(volume, 20)
    ret_5d = close.pct_change(5).iloc[-1]
    if not pd.isna(ret_5d) and not pd.isna(vol_ratio_5):
        if ret_5d > 0 and vol_ratio_5 > 1:
            pv_trend = "放量上涨"
        elif ret_5d < 0 and vol_ratio_5 > 1:
            pv_trend = "放量下跌"
        elif ret_5d > 0:
            pv_trend = "缩量上涨"
        else:
            pv_trend = "缩量下跌"
    else:
        pv_trend = "无数据"

    moneyflow_text = "无数据"
    if not dm._is_us_stock(symbol):
        try:
            flow_df = get_moneyflow(symbol,
                                    (pd.to_datetime(date) - timedelta(days=5)).strftime('%Y%m%d'),
                                    date)
            if not flow_df.empty and 'buy_elg_amount' in flow_df.columns:
                total = flow_df['buy_elg_amount'].sum()
                moneyflow_text = f"近5日主力净买入(超大单): {total:.2f}万元"
        except:
            pass

    # ---- 技术形态 ----
    rsi_14 = calc_rsi(close, 14)
    k, d, j = calc_kdj(high, low, close)
    macd_val, signal_val, hist_val = calc_macd(close)
    macd_desc = "金叉" if (macd_val is not None and signal_val is not None and macd_val > signal_val) else "死叉"
    if upper is not None and not pd.isna(upper) and lower is not None and not pd.isna(lower):
        bb_pos = (close.iloc[-1] - lower) / (upper - lower) if (upper - lower) != 0 else 0.5
    else:
        bb_pos = 0.5
    bb_squeeze = (bb_width is not None and not pd.isna(bb_width) and bb_width < 0.05)

    # ---- 相对强弱 ----
    if close_index is not None:
        idx_mom_20 = calc_momentum(close_index, 20)
        idx_mom_60 = calc_momentum(close_index, 60)
        vs_idx_20 = mom_20 - idx_mom_20
        vs_idx_60 = mom_60 - idx_mom_60
        ret_stock = close.pct_change().dropna()
        ret_idx = close_index.pct_change().dropna()
        common = ret_stock.index.intersection(ret_idx.index)
        if len(common) > 20:
            cov = ret_stock[common].cov(ret_idx[common])
            var = ret_idx[common].var()
            beta = cov / var if var != 0 else 1.0
        else:
            beta = 1.0
        if len(common) > 60:
            alpha = (mom_60 - 0.03) - beta * (idx_mom_60 - 0.03)
        else:
            alpha = None
    else:
        vs_idx_20 = vs_idx_60 = beta = alpha = None

    # ---- 基本面 ----
    profile = {
        "symbol": symbol,
        "date": date,
        "latest_price": round(float(close.iloc[-1]), 2),
        "change_pct": round(float(close.pct_change().iloc[-1] * 100), 2),
        "trend": {
            "short_momentum_20d": round(float(mom_20) if not pd.isna(mom_20) else 0, 4),
            "long_momentum_60d": round(float(mom_60) if not pd.isna(mom_60) else 0, 4),
            "ma_arrangement": ma_arr,
            "near_high_60d": bool(near_high),
            "near_low_60d": bool(near_low)
        },
        "volatility": {
            "daily_vol_20d": round(float(vol_20_abs) if not pd.isna(vol_20_abs) else 0, 4),
            "vol_percentile": round(float(vol_percentile) if not pd.isna(vol_percentile) else 0, 4),
            "bb_width_percentile": round(float(bb_width) if not pd.isna(bb_width) else 0, 4),
            "atr_pct": round(float(atr_val / close.iloc[-1] * 100) if not pd.isna(atr_val) else 0, 2)
        },
        "volume": {
            "volume_ratio_5d": round(float(vol_ratio_5) if not pd.isna(vol_ratio_5) else 0, 4),
            "volume_ratio_20d": round(float(vol_ratio_20) if not pd.isna(vol_ratio_20) else 0, 4),
            "price_volume_trend": pv_trend,
            "moneyflow_5d": moneyflow_text
        },
        "technical": {
            "rsi_14": round(float(rsi_14) if not pd.isna(rsi_14) else 0, 2),
            "kdj_k": round(float(k) if not pd.isna(k) else 0, 2),
            "kdj_d": round(float(d) if not pd.isna(d) else 0, 2),
            "macd_signal": macd_desc,
            "bollinger_position": round(float(bb_pos), 2),
            "bollinger_squeeze": bool(bb_squeeze)
        },
        "relative_strength": {
            "vs_index_20d": round(float(vs_idx_20), 4) if vs_idx_20 is not None else None,
            "vs_index_60d": round(float(vs_idx_60), 4) if vs_idx_60 is not None else None,
            "beta": round(float(beta), 4) if beta is not None else None,
            "alpha_60d": round(float(alpha), 4) if alpha is not None else None
        },
        "fundamental": {
            "pe": fund.get('PE'),
            "pb": fund.get('PB'),
            "roe": fund.get('ROE(%)'),
            "market_cap": fund.get('市值(亿)')
        }
    }
    return profile
