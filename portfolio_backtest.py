
# portfolio_backtest.py
import pandas as pd
import numpy as np
from tqdm import tqdm
from data_utils import get_stock_data
from stock_pool import get_predefined_pool
from factor_calc import get_all_factors_batch
from factor_preprocess import preprocess_factors
from backtest import calculate_metrics

def portfolio_backtest(start_date, end_date, stock_pool_name='demo', stock_list=None, top_n=10,
                       rebalance_freq='M', factor_weights=None,
                       commission=0.001, slippage=0.001):
    """
    多股票组合回测
    返回: daily_nav, benchmark_nav, holdings, metrics, factors_history
    factors_history: list of (date, factor_df)
    """
    # 确定股票列表
    if stock_list is not None:
        stock_list = stock_list
    else:
        stock_list = get_predefined_pool(stock_pool_name)
    
    top_n = min(top_n, len(stock_list))
    start = pd.to_datetime(start_date)
    end = pd.to_datetime(end_date)

    # 生成调仓日期
    all_dates = pd.date_range(start, end, freq='D')
    if rebalance_freq == 'M':
        rebalance_dates = [d for d in all_dates if d.is_month_end and start <= d <= end]
    elif rebalance_freq == 'Q':
        rebalance_dates = [d for d in all_dates if d.is_month_end and d.month in [3,6,9,12] and start <= d <= end]
    else:
        raise ValueError("rebalance_freq 必须是 'M' 或 'Q'")

    if factor_weights is None:
        factor_weights = {
            'momentum': 0.05,
            'reversal': 0.05,
            'volatility': 0.10,
            'rpv': 0.30,
            'new_momentum': 0.30,
            'combo': 0.20,
        }
    factor_cols = list(factor_weights.keys())

    daily_nav = pd.Series(1.0, index=pd.date_range(start, end, freq='D'))
    holdings = {}
    prev_holdings = []
    factors_history = []  # 新增：存储每期因子数据

    for i, rebal_date in enumerate(tqdm(rebalance_dates, desc="组合回测")):
        factors_batch = get_all_factors_batch(stock_list, rebal_date)
        if not factors_batch:
            continue
        factor_df = pd.DataFrame(factors_batch).T
        factor_df = preprocess_factors(factor_df, factor_cols)
        
        # 记录该期因子数据（用于历史查看）
        factors_history.append((rebal_date, factor_df.copy()))
        
        score = pd.Series(0, index=factor_df.index)
        for col, w in factor_weights.items():
            if col in factor_df.columns:
                score += factor_df[col] * w
        selected = score.nlargest(top_n).index.tolist()
        holdings[rebal_date] = selected

        # 调仓成本
        trade_cost_ratio = 0.0
        if i > 0:
            trade_cost_ratio = (commission + slippage) * 2

        # 计算下一个持有期的每日收益
        if i + 1 < len(rebalance_dates):
            next_date = rebalance_dates[i + 1]
        else:
            next_date = end
        period_dates = pd.date_range(rebal_date + pd.Timedelta(days=1), next_date, freq='D')
        for j, dt in enumerate(period_dates):
            daily_ret = 0.0
            cnt = 0
            for stock in selected:
                df_stock = get_stock_data(stock, dt.strftime('%Y%m%d'), dt.strftime('%Y%m%d'))
                if not df_stock.empty and 'return' in df_stock.columns:
                    ret = df_stock['return'].iloc[0]
                    if not np.isnan(ret):
                        daily_ret += ret
                        cnt += 1
            if cnt > 0:
                daily_ret /= cnt
            if j == 0 and trade_cost_ratio > 0:
                daily_ret -= trade_cost_ratio

            prev_nav = daily_nav[daily_nav.index < dt].iloc[-1] if len(daily_nav[daily_nav.index < dt]) > 0 else 1.0
            daily_nav[dt] = prev_nav * (1 + daily_ret)

        prev_holdings = selected

    # 基准净值（沪深300，使用 Tushare）
    import tushare as ts
    try:
        pro = ts.pro_api()
        df_index = pro.index_daily(ts_code='000300.SH', start_date=start_date, end_date=end_date)
        if not df_index.empty:
            df_index['trade_date'] = pd.to_datetime(df_index['trade_date'])
            df_index.set_index('trade_date', inplace=True)
            df_index = df_index.sort_index()
            df_index['return'] = df_index['close'].pct_change()
            benchmark_nav = (1 + df_index['return']).cumprod()
            benchmark_nav = benchmark_nav.reindex(daily_nav.index, method='ffill').fillna(1)
            benchmark_return = df_index['return'].reindex(daily_nav.index, method='ffill').fillna(0)
        else:
            raise ValueError("指数数据为空")
    except Exception as e:
        print(f"获取基准数据失败: {e}")
        benchmark_nav = pd.Series(1.0, index=daily_nav.index)
        benchmark_return = pd.Series(0.0, index=daily_nav.index)

    temp_df = pd.DataFrame({
        'strategy_net': daily_nav,
        'benchmark_net': benchmark_nav,
        'strategy_return': daily_nav.pct_change().fillna(0),
        'return': benchmark_return
    })
    metrics = calculate_metrics(temp_df)
    metrics['选股数量'] = top_n
    metrics['调仓次数'] = len(rebalance_dates)

    return daily_nav, benchmark_nav, holdings, metrics, factors_history