import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import pandas as pd

def plot_stock_analysis(df, title="股票技术分析图"):
    """
    绘制三合一子图：
    - 子图1：收盘价 + 移动平均线 (MA5, MA20, MA60)
    - 子图2：成交量柱状图
    - 子图3：RSI 曲线（带30/70超买超卖线）
    """
    if df.empty:
        print("无数据，无法绘图")
        return

    fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(12, 10), sharex=True)
    
    # 子图1：价格和均线
    ax1.plot(df.index, df['close'], label='Close', linewidth=1.5)
    if 'MA5' in df.columns:
        ax1.plot(df.index, df['MA5'], label='MA5', alpha=0.7)
    if 'MA20' in df.columns:
        ax1.plot(df.index, df['MA20'], label='MA20', alpha=0.7)
    if 'MA60' in df.columns:
        ax1.plot(df.index, df['MA60'], label='MA60', alpha=0.7)
    ax1.set_ylabel('价格 (元)')
    ax1.legend(loc='upper left')
    ax1.grid(True, alpha=0.3)
    ax1.set_title(title)
    
    # 子图2：成交量
    ax2.bar(df.index, df['volume'], color='gray', alpha=0.6, width=0.8)
    ax2.set_ylabel('成交量 (手)')
    ax2.grid(True, alpha=0.3)
    
    # 子图3：RSI
    if 'RSI_14' in df.columns:
        ax3.plot(df.index, df['RSI_14'], label='RSI(14)', color='purple', linewidth=1.5)
        ax3.axhline(70, linestyle='--', color='r', alpha=0.7, label='超买线(70)')
        ax3.axhline(30, linestyle='--', color='g', alpha=0.7, label='超卖线(30)')
        ax3.set_ylabel('RSI')
        ax3.set_ylim(0, 100)
        ax3.legend(loc='upper left')
    else:
        ax3.text(0.5, 0.5, 'RSI 未计算', transform=ax3.transAxes, ha='center')
    ax3.grid(True, alpha=0.3)
    
    # 格式化x轴日期
    ax3.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
    ax3.xaxis.set_major_locator(mdates.MonthLocator(interval=3))
    plt.xticks(rotation=45)
    plt.tight_layout()
    return fig

def plot_equity_curve(df, benchmark_col='benchmark_net', strategy_col='strategy_net'):
    """
    绘制资金曲线对比图（策略 vs 基准）
    注：回测模块完成后使用
    """
    fig, ax = plt.subplots(figsize=(12, 6))
    if strategy_col in df.columns:
        ax.plot(df.index, df[strategy_col], label='策略净值', linewidth=1.5)
    if benchmark_col in df.columns:
        ax.plot(df.index, df[benchmark_col], label='买入持有基准', linewidth=1.5, alpha=0.7)
    ax.set_ylabel('累计净值')
    ax.set_xlabel('日期')
    ax.legend(loc='upper left')
    ax.grid(True, alpha=0.3)
    ax.set_title('策略资金曲线 vs 基准曲线')
    plt.xticks(rotation=45)
    plt.tight_layout()
    return fig

if __name__ == "__main__":
    # 测试绘图
    from data_utils import get_stock_data
    from indicators import compute_all_indicators
    
    df = get_stock_data("000568", "20250201", "20250228")
    df = compute_all_indicators(df)
    fig = plot_stock_analysis(df, title="贵州茅台 2025年技术分析")
    plt.show()