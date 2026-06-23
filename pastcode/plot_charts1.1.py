import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.patches as mpatches
import pandas as pd
import numpy as np

# 设置全局样式
plt.rcParams['font.family'] = 'SimHei'  # 正常显示中文（Windows）
plt.rcParams['axes.unicode_minus'] = False  # 正常显示负号
plt.rcParams['figure.dpi'] = 100          # 基础分辨率
plt.rcParams['savefig.dpi'] = 150         # 保存图片分辨率

def plot_stock_analysis(df, title="股票技术分析图", show_vol_colors=True):
    """
    增强版股票技术分析图
    - df: 包含 open, high, low, close, volume 和可选 MA5/MA20/MA60/RSI_14 等列的 DataFrame
    - show_vol_colors: 成交量柱是否根据涨跌着色（红涨绿跌）
    """
    if df.empty:
        print("无数据，无法绘图")
        return

    # 准备数据（取最近300个交易日，避免数据过多导致拥挤）
    plot_df = df.iloc[-300:].copy() if len(df) > 300 else df.copy()
    
    # 创建子图（价格/成交量/RSI 高度比例 3:1:1.5）
    fig = plt.figure(figsize=(14, 10))
    gs = fig.add_gridspec(3, 1, height_ratios=[3, 1, 1.5], hspace=0.08)
    ax1 = fig.add_subplot(gs[0])
    ax2 = fig.add_subplot(gs[1], sharex=ax1)
    ax3 = fig.add_subplot(gs[2], sharex=ax1)
    
    # ========== 子图1: 价格与均线 ==========
    # 收盘价线条
    ax1.plot(plot_df.index, plot_df['close'], 
             label='收盘价', color='black', linewidth=1.5, alpha=0.9)
    
    # 均线（如果存在）
    if 'MA5' in plot_df.columns:
        ax1.plot(plot_df.index, plot_df['MA5'], 
                 label='MA5', color='blue', linewidth=1, alpha=0.7, linestyle='-')
    if 'MA20' in plot_df.columns:
        ax1.plot(plot_df.index, plot_df['MA20'], 
                 label='MA20', color='orange', linewidth=1.2, alpha=0.8, linestyle='--')
    if 'MA60' in plot_df.columns:
        ax1.plot(plot_df.index, plot_df['MA60'], 
                 label='MA60', color='red', linewidth=1.2, alpha=0.8, linestyle='-.')
    
    # 布林带（如果存在）
    if 'BB_upper' in plot_df.columns and 'BB_lower' in plot_df.columns:
        ax1.fill_between(plot_df.index, plot_df['BB_upper'], plot_df['BB_lower'], 
                         alpha=0.1, color='gray', label='布林带')
        ax1.plot(plot_df.index, plot_df['BB_upper'], color='gray', linewidth=0.8, alpha=0.5, linestyle=':')
        ax1.plot(plot_df.index, plot_df['BB_lower'], color='gray', linewidth=0.8, alpha=0.5, linestyle=':')
    
    ax1.set_ylabel('价格 (元)', fontsize=11)
    ax1.legend(loc='upper left', fontsize=9)
    ax1.grid(True, linestyle='--', alpha=0.5)
    ax1.set_title(title, fontsize=14, fontweight='bold')
    
    # ========== 子图2: 成交量 ==========
    # 根据涨跌给成交量柱着色
    if show_vol_colors and 'close' in plot_df.columns:
        # 计算当日涨跌（与前一日收盘价比较）
        price_change = plot_df['close'].diff()
        colors = ['red' if x > 0 else 'green' if x < 0 else 'gray' for x in price_change]
        ax2.bar(plot_df.index, plot_df['volume'], width=0.8, color=colors, alpha=0.7)
    else:
        ax2.bar(plot_df.index, plot_df['volume'], width=0.8, color='steelblue', alpha=0.7)
    
    ax2.set_ylabel('成交量 (手)', fontsize=11)
    ax2.grid(True, linestyle='--', alpha=0.3)
    
    # ========== 子图3: RSI ==========
    if 'RSI_14' in plot_df.columns:
        ax3.plot(plot_df.index, plot_df['RSI_14'], 
                 label='RSI(14)', color='purple', linewidth=1.5)
        # 超买超卖线
        ax3.axhline(70, linestyle='--', color='red', alpha=0.7, linewidth=1)
        ax3.axhline(30, linestyle='--', color='green', alpha=0.7, linewidth=1)
        # 填充超买超卖区域
        ax3.fill_between(plot_df.index, 70, 100, alpha=0.1, color='red')
        ax3.fill_between(plot_df.index, 0, 30, alpha=0.1, color='green')
        ax3.set_ylim(0, 100)
        ax3.set_ylabel('RSI', fontsize=11)
        ax3.legend(loc='upper left', fontsize=9)
    else:
        ax3.text(0.5, 0.5, 'RSI 未计算', transform=ax3.transAxes, ha='center', va='center', fontsize=12)
        ax3.set_ylim(0, 1)
    
    ax3.set_xlabel('日期', fontsize=11)
    ax3.grid(True, linestyle='--', alpha=0.3)
    
    # ========== 格式化 x 轴日期 ==========
    # 设置日期显示格式（每月1号显示）
    locator = mdates.MonthLocator(interval=2)   # 每两个月显示一个刻度
    formatter = mdates.DateFormatter('%Y-%m')
    ax3.xaxis.set_major_locator(locator)
    ax3.xaxis.set_major_formatter(formatter)
    # 可选：增加每周刻度但只显示小刻度线
    ax3.xaxis.set_minor_locator(mdates.WeekdayLocator(byweekday=mdates.MO))
    ax3.tick_params(axis='x', rotation=45, labelsize=9)
    
    # 自动调整布局
    plt.tight_layout()
    return fig

def plot_equity_curve(df, benchmark_col='benchmark_net', strategy_col='strategy_net'):
    """增强版资金曲线对比图"""
    fig, ax = plt.subplots(figsize=(12, 6))
    
    if strategy_col in df.columns:
        ax.plot(df.index, df[strategy_col], label='策略净值', linewidth=2, color='blue')
    if benchmark_col in df.columns:
        ax.plot(df.index, df[benchmark_col], label='买入持有基准', linewidth=1.5, alpha=0.8, color='gray')
    
    # 填充分离区域（策略超额收益）
    if strategy_col in df.columns and benchmark_col in df.columns:
        ax.fill_between(df.index, df[strategy_col], df[benchmark_col], 
                        where=(df[strategy_col] >= df[benchmark_col]), 
                        color='green', alpha=0.3, label='超额收益')
        ax.fill_between(df.index, df[strategy_col], df[benchmark_col], 
                        where=(df[strategy_col] < df[benchmark_col]), 
                        color='red', alpha=0.3, label='超额亏损')
    
    ax.set_ylabel('累计净值', fontsize=11)
    ax.set_xlabel('日期', fontsize=11)
    ax.legend(loc='upper left')
    ax.grid(True, linestyle='--', alpha=0.5)
    ax.set_title('策略资金曲线 vs 基准曲线', fontsize=14, fontweight='bold')
    
    # 格式化 x 轴日期
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
    ax.xaxis.set_major_locator(mdates.MonthLocator(interval=3))
    plt.xticks(rotation=45)
    plt.tight_layout()
    return fig

if __name__ == "__main__":
    # 测试代码（假设已有数据）
    from data_utils import get_stock_data
    from indicators import compute_all_indicators
    
    df = get_stock_data("000568", "20250201", "20250228")
    df = compute_all_indicators(df)
    fig = plot_stock_analysis(df, title="贵州茅台 2025年技术分析")
    plt.show()