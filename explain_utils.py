import streamlit as st
import pandas as pd
import numpy as np

def indicator_glossary():
    """指标百科折叠面板内容（原有）"""
    st.markdown("""
    ### 📚 指标百科 – 每个指标都在说什么？

    ---
    **1. 基础数据**
    - **开盘价、最高价、最低价、收盘价**：代表一天中股票交易的四个关键价格。收盘价是每日结算基准，最高/最低反映当日波动范围。
    - **成交量**：当天成交的总股数（手）。成交量放大通常意味着市场参与度高，价格变动更可信。
    - **涨跌幅**：（今日收盘-昨日收盘）/昨日收盘，直观反映当日盈亏比例。

    **2. 移动平均线 (MA)**
    - **算法**：过去N日收盘价的算术平均值。
    - **含义**：平滑价格波动，识别趋势方向。短期MA（如5日）对价格反应快，长期MA（如60日）反映主要趋势。金叉（短期上穿长期）看涨，死叉看跌。

    **3. RSI（相对强弱指数）**
    - **算法**：RSI = 100 - 100/(1+RS)，其中RS = 平均上涨幅度/平均下跌幅度（通常14天）。
    - **含义**：衡量股价涨跌的速度和幅度。RSI>70视为超买（可能回调），RSI<30视为超卖（可能反弹）。适合震荡行情。

    **4. 布林带**
    - **算法**：中轨 = MA20，上轨 = 中轨 + k×标准差，下轨 = 中轨 - k×标准差（k常取2）。
    - **含义**：股价通常在上轨和下轨之间波动。触及上轨可能超买，触及下轨可能超卖。带宽收窄预示变盘。

    **5. MACD**
    - **算法**：快线(12日EMA) - 慢线(26日EMA) = DIF，再对DIF做9日EMA得到DEA，柱状图 = DIF - DEA。
    - **含义**：金叉（DIF上穿DEA）买入信号，死叉卖出。柱状图由负转正看涨。

    **6. KDJ**
    - **算法**：基于9日内最高、最低、收盘计算RSV，再平滑得K、D、J。
    - **含义**：K、D值<20超卖，>80超买。金叉买入，死叉卖出。适合短线。

    **7. 成交量比率**
    - **算法**：当前成交量 / 过去20日均量。
    - **含义**：>1表示放量，<1表示缩量。价涨量增是健康趋势。

    **8. 策略信号**
    - **双均线金叉/死叉**：趋势跟踪信号，金叉（短期>长期）买入，死叉卖出。
    - **RSI超卖/超买**：均值回归信号，超卖买入，超买卖出。
    - **布林带触及**：价格触及下轨可能反弹，触及上轨可能回落。
    """)

def explain_main_indicators():
    """主图指标（均线、布林带）的详细解释"""
    st.markdown("""
    **📈 主图指标解释**

    - **MA5**：5日移动平均线，代表最近5个交易日收盘价的平均值。它反映股价的短期趋势，对价格变化敏感，适合短线参考。
    - **MA20**：20日移动平均线（月线），常作为中期趋势的分水岭。股价站稳MA20之上通常表示中期强势，跌破则可能走弱。
    - **MA60**：60日移动平均线（季线），用于判断长期趋势方向。当MA60向上倾斜时，表明股票处于长期上升通道。
    - **布林带（Bollinger Bands）**：
      - **中轨**：即MA20，代表股价的平衡位置。
      - **上轨**：中轨 + 2倍标准差，是价格的压力线。股价触及或突破上轨时，可能进入超买区域，需警惕回调。
      - **下轨**：中轨 - 2倍标准差，是价格的支撑线。股价触及或跌破下轨时，可能进入超卖区域，存在反弹机会。
    - **使用技巧**：当短期均线（MA5）上穿长期均线（MA20或MA60）形成“金叉”时，通常视为买入信号；下穿形成“死叉”时视为卖出信号。布林带收窄（上下轨靠近）往往预示股价将发生剧烈波动。
    """)

def explain_rsi():
    """RSI 指标详细解释"""
    st.markdown("""
    **📉 RSI（相对强弱指数）指标解释**

    - **算法**：RSI = 100 - 100/(1+RS)，其中RS = 过去N日平均上涨幅度 / 过去N日平均下跌幅度（N默认为14）。
    - **取值范围**：0～100。
    - **含义**：
      - **RSI > 70**：超买区，股价可能过高，面临回调风险。
      - **RSI < 30**：超卖区，股价可能过低，存在反弹机会。
      - **30 < RSI < 70**：正常区间，趋势不明显。
    - **使用技巧**：
      - 在震荡行情中，RSI 超卖买入、超买卖出的策略效果较好。
      - 在单边上涨趋势中，RSI可能长期维持在70以上，此时不宜盲目卖出。
      - 当RSI与股价走势出现背离（股价创新高但RSI未创新高）时，可能是趋势反转的信号。
    """)

def explain_macd():
    """MACD 指标详细解释"""
    st.markdown("""
    **📉 MACD（异同移动平均线）指标解释**

    - **算法**：
      - 快线（DIF）= 12日EMA - 26日EMA
      - 慢线（DEA）= DIF的9日EMA
      - 柱状线（BAR）= DIF - DEA
    - **含义**：
      - **金叉**：DIF从下方向上穿过DEA，通常视为买入信号。
      - **死叉**：DIF从上方向下穿过DEA，通常视为卖出信号。
      - **柱状线**：由负转正表示多头力量增强，由正转负表示空头力量增强。
    - **使用技巧**：
      - 零轴上方金叉信号更强，零轴下方死叉信号更可信。
      - 柱状线持续伸长说明趋势在加强，缩短说明趋势减弱。
    """)

def explain_kdj():
    """KDJ 指标详细解释"""
    st.markdown("""
    **📉 KDJ（随机指标）指标解释**

    - **算法**：基于9日内最高价、最低价、收盘价计算RSV，再平滑得到K、D、J三条线。
    - **取值范围**：K、D值通常介于0～100之间。
    - **含义**：
      - **超买**：K、D值 > 80，股价可能过高，面临回调。
      - **超卖**：K、D值 < 20，股价可能过低，存在反弹。
      - **金叉**：K线上穿D线，买入信号。
      - **死叉**：K线下穿D线，卖出信号。
    - **使用技巧**：
      - 结合股价走势：当KDJ金叉发生在超卖区域（K<20）时，信号可靠性更高。
      - 注意钝化：在强趋势中，KDJ可能长时间处于超买或超卖区域，此时不宜逆势操作。
    """)

def explain_signal(row, strategy_type, params):
    """策略信号自然语言解释器（原有）"""
    if strategy_type == "双均线":
        short_ma = params['short_ma']
        long_ma = params['long_ma']
        short_val = row.get(f'MA{short_ma}', 0)
        long_val = row.get(f'MA{long_ma}', 0)
        if row['signal'] == 1:
            return f"📢 **买入信号**：{short_ma}日均线 ({short_val:.2f}) 上穿 {long_ma}日均线 ({long_val:.2f})，通常预示上涨趋势启动。"
        elif row['signal'] == -1:
            return f"📢 **卖出信号**：{short_ma}日均线 ({short_val:.2f}) 下穿 {long_ma}日均线 ({long_val:.2f})，可能进入下跌通道。"
    elif strategy_type == "RSI策略":
        period = params['period']
        rsi_val = row.get(f'RSI_{period}', 0)
        if row['signal'] == 1:
            return f"📢 **买入信号**：RSI({period}) = {rsi_val:.1f}，低于超卖线 {params['oversold']}，历史上超卖后反弹概率较大。"
        elif row['signal'] == -1:
            return f"📢 **卖出信号**：RSI({period}) = {rsi_val:.1f}，高于超买线 {params['overbought']}，可能回调。"
    elif strategy_type == "布林带策略":
        if row['signal'] == 1:
            return f"📢 **买入信号**：收盘价 ({row['close']:.2f}) 触及布林带下轨 ({row['BB_lower']:.2f})，可能超卖反弹。"
        elif row['signal'] == -1:
            return f"📢 **卖出信号**：收盘价 ({row['close']:.2f}) 触及布林带上轨 ({row['BB_upper']:.2f})，可能超买回落。"
    return ""

def explain_pe(pe):
    if pe is None:
        return "暂无数据"
    if pe > 50:
        return "市盈率较高，可能高估，需关注成长性是否匹配。"
    elif pe < 10:
        return "市盈率较低，可能存在低估机会，但需排除基本面恶化的股票。"
    else:
        return "市盈率处于合理区间。"

def explain_pb(pb):
    if pb is None:
        return "暂无数据"
    if pb > 5:
        return "市净率较高，市场给予较高资产溢价，需警惕估值泡沫。"
    elif pb < 1:
        return "市净率低于1，可能跌破净资产，存在价值回归机会，需确认资产质量。"
    else:
        return "市净率合理。"

def signal_historical_performance(df, lookforward_days=[1,5,10,20]):
    """统计历史上买入信号后的收益表现"""
    buy_signals = df[df['signal'] == 1].index
    if len(buy_signals) == 0:
        return None
    stats = {}
    for days in lookforward_days:
        rets = []
        for date in buy_signals:
            future_df = df.loc[date:].iloc[1:]
            if len(future_df) >= days:
                cum_ret = (1 + future_df['return'].iloc[:days]).prod() - 1
                rets.append(cum_ret)
        if rets:
            stats[f'后{days}日'] = {'平均收益': np.mean(rets), '胜率': np.mean(np.array(rets)>0)}
    return stats