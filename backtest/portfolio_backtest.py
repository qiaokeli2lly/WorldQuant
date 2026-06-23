# backtest/portfolio_backtest.py
import pandas as pd
import numpy as np
from tqdm import tqdm
from data.stock_data import get_stock_data
from data.index_data import get_index_data
from factors.preprocessing import preprocess_factors
from backtest.metrics import calculate_metrics
from data.fundamental import pro as ts_pro
from config import DEFAULT_FACTOR_WEIGHTS


def _get_daily_valuation(symbols, start_date, end_date):
    """
    获取多只股票的每日 PE、PB 数据（带本地缓存）。
    返回 {symbol: DataFrame with columns ['PE','PB']}
    """
    import time
    import json
    import os
    from data.fundamental import get_value_factors

    cache_dir = "fundamental_cache"
    os.makedirs(cache_dir, exist_ok=True)
    value_dict = {}
    missing_symbols = list(symbols)

    # 1. 从缓存加载
    for sym in symbols:
        cache_file = os.path.join(cache_dir, f"{sym}_daily_valuation.json")
        if os.path.exists(cache_file):
            try:
                with open(cache_file, 'r') as f:
                    cached = json.load(f)
                df = pd.DataFrame(cached).T
                df.index = pd.to_datetime(df.index)
                df = df.sort_index()
                if not df.empty and df.index.min() <= pd.to_datetime(start_date) and df.index.max() >= pd.to_datetime(end_date):
                    value_dict[sym] = df[['PE', 'PB']]
                    missing_symbols.remove(sym)
            except:
                pass

    # 2. 批量获取缺失
    if missing_symbols and ts_pro is not None:
        try:
            ts_codes = []
            sym_map = {}
            for sym in missing_symbols:
                if sym.startswith('6'):
                    code = f"{sym}.SH"
                else:
                    code = f"{sym}.SZ"
                ts_codes.append(code)
                sym_map[code] = sym

            if ts_codes:
                df_batch = ts_pro.daily_basic(
                    ts_code=','.join(ts_codes),
                    start_date=start_date,
                    end_date=end_date,
                    fields='ts_code,trade_date,pe_ttm,pb'
                )
                if not df_batch.empty:
                    df_batch['trade_date'] = pd.to_datetime(df_batch['trade_date'])
                    for ts_code, group in df_batch.groupby('ts_code'):
                        sym = sym_map.get(ts_code)
                        if not sym:
                            continue
                        group = group.set_index('trade_date')
                        group = group[~group.index.duplicated(keep='first')]
                        group = group.rename(columns={'pe_ttm': 'PE', 'pb': 'PB'})
                        group['PE'] = pd.to_numeric(group['PE'], errors='coerce')
                        group['PB'] = pd.to_numeric(group['PB'], errors='coerce')
                        # 合并可能已有的旧缓存
                        if sym in value_dict:
                            old = value_dict[sym]
                            group = pd.concat([old, group]).sort_index()
                            group = group[~group.index.duplicated(keep='first')]
                        # 保存缓存
                        save_dict = {dt.strftime('%Y-%m-%d'): {'PE': row['PE'], 'PB': row['PB']}
                                     for dt, row in group.iterrows()}
                        with open(os.path.join(cache_dir, f"{sym}_daily_valuation.json"), 'w') as f:
                            json.dump(save_dict, f)
                        value_dict[sym] = group[['PE', 'PB']]
                        if sym in missing_symbols:
                            missing_symbols.remove(sym)
        except Exception as e:
            print(f"批量获取估值失败: {e}")

    # 3. 逐只补缺
    for sym in missing_symbols:
        try:
            if ts_pro is None:
                break
            df_val = get_value_factors(sym, start_date, end_date)
            if df_val is not None and not df_val.empty:
                cols = [c for c in ['PE', 'PB'] if c in df_val.columns]
                if cols:
                    df_clean = df_val[cols].copy()
                    if sym in value_dict:
                        old = value_dict[sym]
                        df_clean = pd.concat([old, df_clean]).sort_index()
                        df_clean = df_clean[~df_clean.index.duplicated(keep='first')]
                    save_dict = {dt.strftime('%Y-%m-%d'): {'PE': row['PE'], 'PB': row['PB']}
                                 for dt, row in df_clean.iterrows()}
                    with open(os.path.join(cache_dir, f"{sym}_daily_valuation.json"), 'w') as f:
                        json.dump(save_dict, f)
                    value_dict[sym] = df_clean
                    missing_symbols.remove(sym)
        except Exception as e:
            print(f"获取 {sym} 估值失败: {e}")
        time.sleep(0.3)

    if missing_symbols:
        print(f"以下股票仍缺少估值数据: {missing_symbols}")
    return value_dict


def _preload_data(stock_list, start, end, use_fundamental=False):
    data_dict = {}
    value_dict = {}
    missing_value_stocks = []

    need_bars = 260 + 60
    preload_start = (start - pd.Timedelta(days=need_bars)).strftime('%Y%m%d')
    preload_end = end.strftime('%Y%m%d')

    for sym in tqdm(stock_list, desc="加载行情数据"):
        # 跳过美股（回测仅支持A股）
        if sym.isalpha():
            print(f"跳过非A股: {sym}")
            continue
        df = get_stock_data(sym, preload_start, preload_end)
        if not df.empty:
            data_dict[sym] = df

    if use_fundamental:
        val_start = start.strftime('%Y%m%d')
        val_end = end.strftime('%Y%m%d')
        value_dict = _get_daily_valuation(stock_list, val_start, val_end)
        for sym in stock_list:
            if sym not in value_dict and not sym.isalpha():
                missing_value_stocks.append(sym)
        if missing_value_stocks:
            print(f"警告：以下 {len(missing_value_stocks)} 只股票缺少估值数据：{missing_value_stocks}")

    return data_dict, value_dict, missing_value_stocks


def _get_benchmark(start, end):
    df = get_index_data('000300.SH', start.strftime('%Y%m%d'), end.strftime('%Y%m%d'))
    if df.empty:
        dates = pd.date_range(start, end, freq='D')
        bench_nav = pd.Series(1.0, index=dates)
        bench_return = pd.Series(0.0, index=dates)
    else:
        df = df.sort_index()
        df = df[~df.index.duplicated(keep='first')]
        df['return'] = df['close'].pct_change()
        bench_nav = (1 + df['return']).cumprod()
        all_dates = pd.date_range(start, end, freq='D')
        bench_nav = bench_nav.reindex(all_dates, method='ffill').fillna(1)
        bench_return = df['return'].reindex(all_dates, method='ffill').fillna(0)
        bench_nav = bench_nav.groupby(bench_nav.index).first()
        bench_return = bench_return.groupby(bench_return.index).first()
    return bench_nav, bench_return


def _get_factors_for_date(symbols, date, data_dict, value_dict, use_fundamental, lookbacks):
    from factors.price_factors import (
        calc_momentum, calc_reversal, calc_volatility,
        calc_rpv, calc_new_momentum, calc_combo_vol_price
    )
    from factors.fundamental_factors import transform_pe, transform_pb

    result = {}
    max_lookback = max(lookbacks.values()) + 60
    for sym in symbols:
        if sym not in data_dict:
            continue
        df_full = data_dict[sym]
        df = df_full.loc[:date]
        if len(df) < max_lookback:
            continue
        df = df.iloc[-max_lookback:]
        close = df['close']
        volume = df['volume'] if 'volume' in df.columns else None

        mom = calc_momentum(close, lookbacks['momentum'])
        rev = calc_reversal(close, lookbacks['reversal'])
        vol = calc_volatility(close, lookbacks['volatility'])
        if any(np.isnan(x) for x in [mom, rev, vol]):
            continue

        rpv = calc_rpv(close, volume, 20) if volume is not None else np.nan
        new_mom = calc_new_momentum(close)
        combo = calc_combo_vol_price(close)

        pe_score = np.nan
        pb_score = np.nan
        if use_fundamental and sym in value_dict:
            val_df = value_dict[sym]
            if date in val_df.index:
                row = val_df.loc[date]
                pe_raw = row.get('PE', np.nan)
                pb_raw = row.get('PB', np.nan)
                pe_score = transform_pe(pe_raw) if not pd.isna(pe_raw) else np.nan
                pb_score = transform_pb(pb_raw) if not pd.isna(pb_raw) else np.nan

        result[sym] = {
            'momentum': mom,
            'reversal': rev,
            'volatility': vol,
            'rpv': rpv,
            'new_momentum': new_mom,
            'combo': combo,
            'pe': pe_score,
            'pb': pb_score,
        }
    return result


def portfolio_backtest(start_date, end_date, stock_list=None, top_n=15,
                       rebalance_freq='M', factor_weights=None,
                       commission=0.001, slippage=0.001):
    start = pd.to_datetime(start_date)
    end = pd.to_datetime(end_date)

    if factor_weights is None:
        factor_weights = DEFAULT_FACTOR_WEIGHTS.copy()
    weight_sum = sum(factor_weights.values())
    if weight_sum > 0:
        factor_weights = {k: v / weight_sum for k, v in factor_weights.items()}
    else:
        n = len(factor_weights)
        factor_weights = {k: 1.0/n for k in factor_weights}

    factor_cols = list(factor_weights.keys())
    use_fundamental = 'pe' in factor_cols or 'pb' in factor_cols

    lookbacks = {'momentum':20, 'reversal':5, 'volatility':20}

    print("预加载数据...")
    data_dict, value_dict, missing_value_stocks = _preload_data(stock_list, start, end, use_fundamental)

    all_dates = pd.date_range(start, end, freq='D')
    if rebalance_freq == 'M':
        rebalance_dates = [d for d in all_dates if d.is_month_end and start <= d <= end]
    elif rebalance_freq == 'Q':
        rebalance_dates = [d for d in all_dates if d.is_month_end and d.month in [3,6,9,12] and start <= d <= end]
    else:
        raise ValueError("rebalance_freq 必须是 'M' 或 'Q'")

    top_n = min(top_n, len(stock_list))
    daily_nav = pd.Series(np.nan, index=pd.date_range(start, end, freq='D'))
    holdings = {}
    factors_history = []
    holdings_detail = {}

    for i, rebal_date in enumerate(tqdm(rebalance_dates, desc="回测")):
        factors = _get_factors_for_date(stock_list, rebal_date, data_dict, value_dict,
                                        use_fundamental, lookbacks)
        if not factors:
            continue
        factor_df = pd.DataFrame(factors).T
        factor_df = factor_df[~factor_df.index.duplicated(keep='first')]
        factor_df = preprocess_factors(factor_df, factor_cols).fillna(0)
        factors_history.append((rebal_date, factor_df.copy()))

        score = pd.Series(0.0, index=factor_df.index)
        for col, w in factor_weights.items():
            if col in factor_df.columns:
                score += factor_df[col] * w
        factor_df['score'] = score
        factor_df['rank'] = score.rank(ascending=False).astype(int)
        selected = score.nlargest(top_n).index.tolist()
        holdings[rebal_date] = selected

        detail_df = factor_df.loc[selected].sort_values('score', ascending=False)
        holdings_detail[rebal_date] = detail_df[['score', 'rank'] + factor_cols]

        trade_cost = 0.0
        if i > 0:
            trade_cost = (commission + slippage) * 2

        if i+1 < len(rebalance_dates):
            next_date = rebalance_dates[i+1]
        else:
            next_date = end
        period = pd.date_range(rebal_date + pd.Timedelta(days=1), next_date, freq='D')
        for dt in period:
            daily_ret = 0.0
            cnt = 0
            for s in selected:
                if s in data_dict and dt in data_dict[s].index:
                    ret = data_dict[s].loc[dt, 'return']
                    if not np.isnan(ret):
                        daily_ret += ret
                        cnt += 1
            if cnt > 0:
                daily_ret /= cnt
            if i > 0 and dt == period[0]:
                daily_ret -= trade_cost

            if pd.isna(daily_nav[dt]):
                prev_nav = daily_nav[daily_nav.index < dt].dropna().iloc[-1] if len(daily_nav[daily_nav.index < dt].dropna()) > 0 else 1.0
                daily_nav[dt] = prev_nav * (1 + daily_ret)

    daily_nav = daily_nav.ffill().fillna(1)

    benchmark_nav, benchmark_return = _get_benchmark(start, end)

    temp_df = pd.DataFrame({
        'strategy_net': daily_nav,
        'benchmark_net': benchmark_nav,
        'strategy_return': daily_nav.pct_change().fillna(0),
        'return': benchmark_return
    })
    metrics = calculate_metrics(temp_df)
    metrics['选股数量'] = top_n
    metrics['调仓次数'] = len(rebalance_dates)
    metrics['估值数据缺失股数'] = len(missing_value_stocks)
    return daily_nav, benchmark_nav, holdings, metrics, factors_history, holdings_detail