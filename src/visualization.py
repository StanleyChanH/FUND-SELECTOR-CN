"""
数据可视化模块
负责创建各种图表和可视化展示
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime

def create_nav_chart(df, benchmark_df=None, show_ma=True, show_boll=False, short_ma=20, long_ma=60):
    """
    创建净值走势与通道指标图表

    Args:
        df: 基金数据DataFrame
        benchmark_df: 基准数据DataFrame（可选）
        show_ma: 是否显示移动平均线
        show_boll: 是否显示布林带
        short_ma: 短期均线周期
        long_ma: 长期均线周期

    Returns:
        plotly.graph_objects.Figure: 图表对象
    """
    if df is None or df.empty:
        return None

    try:
        fig = go.Figure()

        # 基金累计净值线
        fig.add_trace(go.Scatter(
            x=df['date'],
            y=df['cum_nav'],
            mode='lines',
            name='基金累计净值',
            line=dict(color='blue', width=2)
        ))

        # 基准指数线（如果提供）
        if benchmark_df is not None and not benchmark_df.empty:
            # 将基准数据归一化
            benchmark_normalized = benchmark_df['close'] / benchmark_df['close'].iloc[0]
            fig.add_trace(go.Scatter(
                x=benchmark_df['trade_date'],
                y=benchmark_normalized,
                mode='lines',
                name='基准指数',
                line=dict(color='gray', width=1, dash='dash')
            ))

        # 移动平均线
        if show_ma:
            short_ma_col = f'MA{short_ma}'
            long_ma_col = f'MA{long_ma}'

            if short_ma_col in df.columns:
                # 归一化移动平均线
                ma_normalized = df[short_ma_col] / df['nav'].iloc[0]
                fig.add_trace(go.Scatter(
                    x=df['date'],
                    y=ma_normalized,
                    mode='lines',
                    name=f'MA{short_ma}',
                    line=dict(color='orange', width=1)
                ))

            if long_ma_col in df.columns:
                # 归一化移动平均线
                ma_normalized = df[long_ma_col] / df['nav'].iloc[0]
                fig.add_trace(go.Scatter(
                    x=df['date'],
                    y=ma_normalized,
                    mode='lines',
                    name=f'MA{long_ma}',
                    line=dict(color='red', width=1)
                ))

        # 布林带
        if show_boll and all(col in df.columns for col in ['BOLL_UPPER', 'BOLL_MIDDLE', 'BOLL_LOWER']):
            # 归一化布林带
            upper_normalized = df['BOLL_UPPER'] / df['nav'].iloc[0]
            middle_normalized = df['BOLL_MIDDLE'] / df['nav'].iloc[0]
            lower_normalized = df['BOLL_LOWER'] / df['nav'].iloc[0]

            fig.add_trace(go.Scatter(
                x=df['date'],
                y=upper_normalized,
                mode='lines',
                name='布林带上轨',
                line=dict(color='lightgray', width=1),
                fill=None
            ))

            fig.add_trace(go.Scatter(
                x=df['date'],
                y=lower_normalized,
                mode='lines',
                name='布林带下轨',
                line=dict(color='lightgray', width=1),
                fill='tonexty',
                fillcolor='rgba(211,211,211,0.2)'
            ))

            fig.add_trace(go.Scatter(
                x=df['date'],
                y=middle_normalized,
                mode='lines',
                name='布林带中轨',
                line=dict(color='gray', width=1, dash='dot')
            ))

        # 添加金叉死叉标记
        golden_cross, death_cross = detect_cross_points(df, short_ma, long_ma)

        if golden_cross:
            golden_dates = [date for date in golden_cross if date in df['date'].values]
            if golden_dates:
                golden_values = [df[df['date'] == date]['cum_nav'].iloc[0] for date in golden_dates]
                fig.add_trace(go.Scatter(
                    x=golden_dates,
                    y=golden_values,
                    mode='markers',
                    name='金叉',
                    marker=dict(color='gold', size=10, symbol='triangle-up')
                ))

        if death_cross:
            death_dates = [date for date in death_cross if date in df['date'].values]
            if death_dates:
                death_values = [df[df['date'] == date]['cum_nav'].iloc[0] for date in death_dates]
                fig.add_trace(go.Scatter(
                    x=death_dates,
                    y=death_values,
                    mode='markers',
                    name='死叉',
                    marker=dict(color='black', size=10, symbol='triangle-down')
                ))

        # 图表布局
        fig.update_layout(
            title='基金净值走势与通道指标',
            xaxis_title='日期',
            yaxis_title='累计净值（归一化）',
            hovermode='x unified',
            legend=dict(
                orientation='h',
                yanchor='bottom',
                y=1.02,
                xanchor='right',
                x=1
            ),
            height=500,
            xaxis=dict(
                range=[df['date'].iloc[0], df['date'].iloc[-1]],
                type='date'
            )
        )

        return fig

    except Exception as e:
        st.error(f"创建净值图表失败: {str(e)}")
        return None

def detect_cross_points(df, short_ma=20, long_ma=60):
    """检测金叉死叉点"""
    try:
        short_col = f'MA{short_ma}'
        long_col = f'MA{long_ma}'

        if short_col not in df.columns or long_col not in df.columns:
            return [], []

        golden_cross = []
        death_cross = []

        for i in range(1, len(df)):
            if (df[short_col].iloc[i-1] <= df[long_col].iloc[i-1] and
                df[short_col].iloc[i] > df[long_col].iloc[i]):
                golden_cross.append(df['date'].iloc[i])

            elif (df[short_col].iloc[i-1] >= df[long_col].iloc[i-1] and
                  df[short_col].iloc[i] < df[long_col].iloc[i]):
                death_cross.append(df['date'].iloc[i])

        return golden_cross, death_cross

    except Exception:
        return [], []

def create_risk_charts(df, rsi_period=14):
    """
    创建风险与相对强弱分析图表

    Args:
        df: 包含技术指标的DataFrame
        rsi_period: RSI周期

    Returns:
        plotly.graph_objects.Figure: 包含子图的图表对象
    """
    if df is None or df.empty:
        return None

    try:
        # 创建子图
        fig = make_subplots(
            rows=2, cols=1,
            subplot_titles=('滚动年化波动率 (60日)', f'相对强弱指数 RSI({rsi_period})'),
            vertical_spacing=0.1
        )

        # 滚动波动率
        if 'rolling_volatility' in df.columns:
            fig.add_trace(
                go.Scatter(
                    x=df['date'],
                    y=df['rolling_volatility'],
                    mode='lines',
                    name='滚动波动率',
                    line=dict(color='blue')
                ),
                row=1, col=1
            )
        else:
            # 计算滚动波动率
            returns = df['nav'].pct_change().dropna()
            rolling_vol = returns.rolling(window=60).std() * np.sqrt(252)
            fig.add_trace(
                go.Scatter(
                    x=df['date'][1:],
                    y=rolling_vol,
                    mode='lines',
                    name='滚动波动率',
                    line=dict(color='blue')
                ),
                row=1, col=1
            )

        # RSI
        rsi_col = f'RSI{rsi_period}'
        if rsi_col in df.columns:
            fig.add_trace(
                go.Scatter(
                    x=df['date'],
                    y=df[rsi_col],
                    mode='lines',
                    name='RSI',
                    line=dict(color='purple')
                ),
                row=2, col=1
            )

            # 添加超买超卖线
            fig.add_hline(y=70, line_dash="dash", line_color="red", row=2, col=1)
            fig.add_hline(y=30, line_dash="dash", line_color="green", row=2, col=1)

        # 更新布局
        fig.update_layout(
            title='风险与相对强弱分析',
            height=600,
            showlegend=True,
            hovermode='x unified',
            xaxis=dict(
                range=[df['date'].iloc[0], df['date'].iloc[-1]],
                type='date'
            ),
            xaxis2=dict(
                range=[df['date'].iloc[0], df['date'].iloc[-1]],
                type='date'
            )
        )

        fig.update_xaxes(title_text='日期', row=2, col=1)
        fig.update_yaxes(title_text='波动率', row=1, col=1)
        fig.update_yaxes(title_text='RSI', row=2, col=1)

        return fig

    except Exception as e:
        st.error(f"创建风险图表失败: {str(e)}")
        return None

def create_technical_indicator_charts(df, selected_indicators):
    """
    创建高级技术指标图表

    Args:
        df: 包含技术指标的DataFrame
        selected_indicators: 用户选择的指标列表

    Returns:
        list: 图表对象列表
    """
    if df is None or df.empty or not selected_indicators:
        return []

    charts = []

    try:
        for indicator in selected_indicators:
            if indicator == 'MACD' and all(col in df.columns for col in ['MACD_DIF', 'MACD_DEA', 'MACD_HIST']):
                fig = go.Figure()

                fig.add_trace(go.Scatter(
                    x=df['date'],
                    y=df['MACD_DIF'],
                    mode='lines',
                    name='DIF',
                    line=dict(color='blue')
                ))

                fig.add_trace(go.Scatter(
                    x=df['date'],
                    y=df['MACD_DEA'],
                    mode='lines',
                    name='DEA',
                    line=dict(color='red')
                ))

                fig.add_trace(go.Bar(
                    x=df['date'],
                    y=df['MACD_HIST'],
                    name='MACD柱',
                    marker_color='green' if df['MACD_HIST'].iloc[-1] > 0 else 'red',
                    yaxis='y2'
                ))

                # 创建双轴布局
                fig.update_layout(
                    title='MACD指标 - 平滑异同移动平均线',
                    xaxis_title='日期',
                    yaxis=dict(title='DIF/DEA', side='left'),
                    yaxis2=dict(title='MACD柱', overlaying='y', side='right'),
                    height=400,
                    legend=dict(x=0, y=1)
                )
                charts.append(fig)

            elif indicator == 'KDJ' and all(col in df.columns for col in ['KDJ_K', 'KDJ_D', 'KDJ_J']):
                fig = go.Figure()

                fig.add_trace(go.Scatter(
                    x=df['date'],
                    y=df['KDJ_K'],
                    mode='lines',
                    name='K线',
                    line=dict(color='blue', width=2)
                ))

                fig.add_trace(go.Scatter(
                    x=df['date'],
                    y=df['KDJ_D'],
                    mode='lines',
                    name='D线',
                    line=dict(color='red', width=2)
                ))

                fig.add_trace(go.Scatter(
                    x=df['date'],
                    y=df['KDJ_J'],
                    mode='lines',
                    name='J线',
                    line=dict(color='green', width=2)
                ))

                # 添加超买超卖线
                fig.add_hline(y=80, line_dash="dash", line_color="red", opacity=0.5, annotation_text="超买线(80)")
                fig.add_hline(y=20, line_dash="dash", line_color="green", opacity=0.5, annotation_text="超卖线(20)")

                fig.update_layout(
                    title='KDJ指标 - 随机指标',
                    xaxis_title='日期',
                    yaxis_title='KDJ值',
                    height=400,
                    yaxis=dict(range=[0, 100])
                )
                charts.append(fig)

            elif indicator == 'CCI' and 'CCI' in df.columns:
                fig = go.Figure()

                fig.add_trace(go.Scatter(
                    x=df['date'],
                    y=df['CCI'],
                    mode='lines',
                    name='CCI',
                    line=dict(color='purple', width=2)
                ))

                # 添加超买超卖线
                fig.add_hline(y=100, line_dash="dash", line_color="red", opacity=0.5, annotation_text="超买线(100)")
                fig.add_hline(y=-100, line_dash="dash", line_color="green", opacity=0.5, annotation_text="超卖线(-100)")
                fig.add_hline(y=0, line_dash="dot", line_color="gray", opacity=0.3)

                fig.update_layout(
                    title='CCI指标 - 顺势指标',
                    xaxis_title='日期',
                    yaxis_title='CCI值',
                    height=400
                )
                charts.append(fig)

            elif indicator == 'DMI' and all(col in df.columns for col in ['DMI_PLUS', 'DMI_MINUS', 'DMI_ADX']):
                fig = go.Figure()

                fig.add_trace(go.Scatter(
                    x=df['date'],
                    y=df['DMI_PLUS'],
                    mode='lines',
                    name='+DI',
                    line=dict(color='green', width=2)
                ))

                fig.add_trace(go.Scatter(
                    x=df['date'],
                    y=df['DMI_MINUS'],
                    mode='lines',
                    name='-DI',
                    line=dict(color='red', width=2)
                ))

                fig.add_trace(go.Scatter(
                    x=df['date'],
                    y=df['DMI_ADX'],
                    mode='lines',
                    name='ADX',
                    line=dict(color='blue', width=2)
                ))

                fig.update_layout(
                    title='DMI指标 - 动向指标',
                    xaxis_title='日期',
                    yaxis_title='DMI值',
                    height=400
                )
                charts.append(fig)

            elif indicator == 'BBI' and 'BBI' in df.columns:
                fig = go.Figure()

                fig.add_trace(go.Scatter(
                    x=df['date'],
                    y=df['nav'],
                    mode='lines',
                    name='净值',
                    line=dict(color='gray', width=1),
                    opacity=0.7
                ))

                fig.add_trace(go.Scatter(
                    x=df['date'],
                    y=df['BBI'],
                    mode='lines',
                    name='BBI多空指标',
                    line=dict(color='orange', width=2)
                ))

                fig.update_layout(
                    title='BBI指标 - 多空指标',
                    xaxis_title='日期',
                    yaxis_title='值',
                    height=400
                )
                charts.append(fig)

            elif indicator == 'TRIX' and all(col in df.columns for col in ['TRIX', 'TRIX_SIGNAL']):
                fig = go.Figure()

                fig.add_trace(go.Scatter(
                    x=df['date'],
                    y=df['TRIX'],
                    mode='lines',
                    name='TRIX',
                    line=dict(color='blue', width=2)
                ))

                fig.add_trace(go.Scatter(
                    x=df['date'],
                    y=df['TRIX_SIGNAL'],
                    mode='lines',
                    name='信号线',
                    line=dict(color='red', width=2)
                ))

                fig.add_hline(y=0, line_dash="dot", line_color="gray", opacity=0.5)

                fig.update_layout(
                    title='TRIX指标 - 三重指数平滑移动平均线',
                    xaxis_title='日期',
                    yaxis_title='TRIX值',
                    height=400
                )
                charts.append(fig)

            elif indicator == 'ATR' and 'ATR' in df.columns:
                fig = go.Figure()

                fig.add_trace(go.Scatter(
                    x=df['date'],
                    y=df['ATR'],
                    mode='lines',
                    name='ATR',
                    line=dict(color='brown', width=2),
                    fill='tonexty'
                ))

                fig.update_layout(
                    title='ATR指标 - 真实波动率',
                    xaxis_title='日期',
                    yaxis_title='ATR值',
                    height=400
                )
                charts.append(fig)

            elif indicator == 'OBV' and 'OBV' in df.columns:
                fig = go.Figure()

                fig.add_trace(go.Scatter(
                    x=df['date'],
                    y=df['OBV'],
                    mode='lines',
                    name='OBV',
                    line=dict(color='purple', width=2)
                ))

                fig.update_layout(
                    title='OBV指标 - 能量潮',
                    xaxis_title='日期',
                    yaxis_title='OBV值',
                    height=400
                )
                charts.append(fig)

            elif indicator == 'MFI' and 'MFI' in df.columns:
                fig = go.Figure()

                fig.add_trace(go.Scatter(
                    x=df['date'],
                    y=df['MFI'],
                    mode='lines',
                    name='MFI',
                    line=dict(color='darkgreen', width=2)
                ))

                # 添加超买超卖线
                fig.add_hline(y=80, line_dash="dash", line_color="red", opacity=0.5, annotation_text="超买线(80)")
                fig.add_hline(y=20, line_dash="dash", line_color="green", opacity=0.5, annotation_text="超卖线(20)")

                fig.update_layout(
                    title='MFI指标 - 资金流量指标',
                    xaxis_title='日期',
                    yaxis_title='MFI值',
                    height=400,
                    yaxis=dict(range=[0, 100])
                )
                charts.append(fig)

            # BOLL布林带在净值走势图中已显示，这里可以单独显示一个更详细的版本
            elif indicator == 'BOLL' and all(col in df.columns for col in ['BOLL_UPPER', 'BOLL_MIDDLE', 'BOLL_LOWER']):
                fig = go.Figure()

                fig.add_trace(go.Scatter(
                    x=df['date'],
                    y=df['nav'],
                    mode='lines',
                    name='净值',
                    line=dict(color='black', width=2)
                ))

                fig.add_trace(go.Scatter(
                    x=df['date'],
                    y=df['BOLL_UPPER'],
                    mode='lines',
                    name='上轨',
                    line=dict(color='red', width=1),
                    fill=None
                ))

                fig.add_trace(go.Scatter(
                    x=df['date'],
                    y=df['BOLL_LOWER'],
                    mode='lines',
                    name='下轨',
                    line=dict(color='red', width=1),
                    fill='tonexty',
                    fillcolor='rgba(255,0,0,0.1)'
                ))

                fig.add_trace(go.Scatter(
                    x=df['date'],
                    y=df['BOLL_MIDDLE'],
                    mode='lines',
                    name='中轨',
                    line=dict(color='blue', width=1, dash='dash')
                ))

                fig.update_layout(
                    title='BOLL指标 - 布林带详细分析',
                    xaxis_title='日期',
                    yaxis_title='净值',
                    height=400
                )
                charts.append(fig)

        return charts

    except Exception as e:
        st.error(f"创建技术指标图表失败: {str(e)}")
        return []

def create_yearly_returns_chart(df, benchmark_df=None):
    """
    创建年度收益对比图表

    Args:
        df: 基金数据DataFrame
        benchmark_df: 基准数据DataFrame（可选）

    Returns:
        plotly.graph_objects.Figure: 图表对象
    """
    if df is None or df.empty:
        return None

    try:
        # 计算年度收益
        df_yearly = df.copy()
        df_yearly['year'] = df_yearly['date'].dt.year

        # 按年分组，计算年度收益率
        yearly_returns = []
        years = []

        for year in df_yearly['year'].unique():
            year_data = df_yearly[df_yearly['year'] == year]
            if len(year_data) > 1:
                year_return = (year_data['cum_nav'].iloc[-1] / year_data['cum_nav'].iloc[0]) - 1
                yearly_returns.append(year_return)
                years.append(year)

        # 创建图表
        fig = go.Figure()

        # 基金年度收益
        fig.add_trace(go.Bar(
            x=years,
            y=yearly_returns,
            name='基金年度收益率',
            marker_color='blue'
        ))

        # 基准年度收益（如果提供）
        if benchmark_df is not None and not benchmark_df.empty:
            benchmark_yearly = benchmark_df.copy()
            benchmark_yearly['year'] = pd.to_datetime(benchmark_yearly['trade_date']).dt.year

            benchmark_yearly_returns = []
            for year in years:
                year_data = benchmark_yearly[benchmark_yearly['year'] == year]
                if len(year_data) > 1:
                    year_return = (year_data['close'].iloc[-1] / year_data['close'].iloc[0]) - 1
                    benchmark_yearly_returns.append(year_return)
                else:
                    benchmark_yearly_returns.append(0)

            fig.add_trace(go.Bar(
                x=years,
                y=benchmark_yearly_returns,
                name='基准年度收益率',
                marker_color='gray'
            ))

        # 添加收益率标签
        fig.update_traces(texttemplate='%{y:.2%}', textposition='outside')

        fig.update_layout(
            title='各年度收益率对比',
            xaxis_title='年份',
            yaxis_title='收益率',
            yaxis_tickformat='.1%',
            barmode='group',
            height=400
        )

        return fig

    except Exception as e:
        st.error(f"创建年度收益图表失败: {str(e)}")
        return None

def generate_technical_analysis_summary(df, selected_indicators):
    """
    生成技术指标投资解读摘要

    Args:
        df: 包含技术指标的DataFrame
        selected_indicators: 已计算的技术指标列表

    Returns:
        dict: 技术指标解读结果
    """
    if df is None or df.empty:
        return None

    try:
        summary = {
            'overall_signal': '中性',
            'key_signals': [],
            'risk_level': '中等',
            'suggestion': '',
            'indicator_analysis': {}
        }

        # 获取最新数据
        latest_data = df.iloc[-1] if len(df) > 0 else None
        if latest_data is None:
            return summary

        signals_bullish = 0  # 看涨信号数
        signals_bearish = 0  # 看跌信号数

        # MACD分析
        if 'MACD_DIF' in df.columns and 'MACD_DEA' in df.columns:
            dif_latest = latest_data['MACD_DIF']
            dea_latest = latest_data['MACD_DEA']
            hist_latest = dif_latest - dea_latest

            macd_signal = '中性'
            if dif_latest > dea_latest and hist_latest > 0:
                macd_signal = '看涨'
                signals_bullish += 1
            elif dif_latest < dea_latest and hist_latest < 0:
                macd_signal = '看跌'
                signals_bearish += 1

            summary['indicator_analysis']['MACD'] = {
                'signal': macd_signal,
                'interpretation': f'MACD显示{macd_signal}信号，DIF为{dif_latest:.6f}，DEA为{dea_latest:.6f}'
            }

        # RSI分析
        rsi_col = [col for col in df.columns if col.startswith('RSI')]
        if rsi_col:
            rsi_latest = latest_data[rsi_col[0]]
            rsi_signal = '中性'
            if rsi_latest > 70:
                rsi_signal = '超买'
                signals_bearish += 1
            elif rsi_latest < 30:
                rsi_signal = '超卖'
                signals_bullish += 1

            summary['indicator_analysis']['RSI'] = {
                'signal': rsi_signal,
                'interpretation': f'RSI为{rsi_latest:.2f}，处于{rsi_signal}区域'
            }

        # KDJ分析
        if all(col in df.columns for col in ['KDJ_K', 'KDJ_D', 'KDJ_J']):
            k_latest = latest_data['KDJ_K']
            d_latest = latest_data['KDJ_D']
            j_latest = latest_data['KDJ_J']

            kdj_signal = '中性'
            if k_latest > 80 and d_latest > 80:
                kdj_signal = '超买'
                signals_bearish += 1
            elif k_latest < 20 and d_latest < 20:
                kdj_signal = '超卖'
                signals_bullish += 1
            elif k_latest > d_latest and j_latest > 0:
                kdj_signal = '看涨'
                signals_bullish += 1
            elif k_latest < d_latest and j_latest < 0:
                kdj_signal = '看跌'
                signals_bearish += 1

            summary['indicator_analysis']['KDJ'] = {
                'signal': kdj_signal,
                'interpretation': f'KDJ为K:{k_latest:.2f}, D:{d_latest:.2f}, J:{j_latest:.2f}，显示{kdj_signal}信号'
            }

        # 布林带分析
        if all(col in df.columns for col in ['BOLL_UPPER', 'BOLL_MIDDLE', 'BOLL_LOWER']):
            nav_latest = latest_data['nav']
            upper_latest = latest_data['BOLL_UPPER']
            lower_latest = latest_data['BOLL_LOWER']
            middle_latest = latest_data['BOLL_MIDDLE']

            boll_signal = '中性'
            if nav_latest > upper_latest:
                boll_signal = '突破上轨'
                signals_bearish += 1  # 可能回调
            elif nav_latest < lower_latest:
                boll_signal = '跌破下轨'
                signals_bullish += 1  # 可能反弹
            elif nav_latest > middle_latest:
                boll_signal = '强势区域'
                signals_bullish += 1
            else:
                boll_signal = '弱势区域'
                signals_bearish += 1

            summary['indicator_analysis']['BOLL'] = {
                'signal': boll_signal,
                'interpretation': f'价格在布林带{boll_signal}，当前位置相对强度明显'
            }

        # CCI分析
        if 'CCI' in df.columns:
            cci_latest = latest_data['CCI']
            cci_signal = '中性'
            if cci_latest > 100:
                cci_signal = '超买'
                signals_bearish += 1
            elif cci_latest < -100:
                cci_signal = '超卖'
                signals_bullish += 1

            summary['indicator_analysis']['CCI'] = {
                'signal': cci_signal,
                'interpretation': f'CCI为{cci_latest:.2f}，显示{cci_signal}信号'
            }

        # DMI分析
        if all(col in df.columns for col in ['DMI_PLUS', 'DMI_MINUS', 'DMI_ADX']):
            di_plus_latest = latest_data['DMI_PLUS']
            di_minus_latest = latest_data['DMI_MINUS']
            adx_latest = latest_data['DMI_ADX']

            dmi_signal = '中性'
            if adx_latest > 25:  # 趋势明显
                if di_plus_latest > di_minus_latest:
                    dmi_signal = '上涨趋势'
                    signals_bullish += 1
                else:
                    dmi_signal = '下跌趋势'
                    signals_bearish += 1
            else:
                dmi_signal = '震荡'

            summary['indicator_analysis']['DMI'] = {
                'signal': dmi_signal,
                'interpretation': f'DMI显示{dmi_signal}，ADX为{adx_latest:.2f}，趋势强度{"较强" if adx_latest > 25 else "较弱"}'
            }

        # MFI分析
        if 'MFI' in df.columns:
            mfi_latest = latest_data['MFI']
            mfi_signal = '中性'
            if mfi_latest > 80:
                mfi_signal = '超买'
                signals_bearish += 1
            elif mfi_latest < 20:
                mfi_signal = '超卖'
                signals_bullish += 1

            summary['indicator_analysis']['MFI'] = {
                'signal': mfi_signal,
                'interpretation': f'MFI为{mfi_latest:.2f}，资金流向显示{mfi_signal}状态'
            }

        # BBI分析
        if 'BBI' in df.columns:
            bbi_latest = latest_data['BBI']
            nav_latest = latest_data['nav']

            bbi_signal = '中性'
            if nav_latest > bbi_latest:
                bbi_signal = '看涨'
                signals_bullish += 1
            else:
                bbi_signal = '看跌'
                signals_bearish += 1

            summary['indicator_analysis']['BBI'] = {
                'signal': bbi_signal,
                'interpretation': f'BBI多空指标显示{bbi_signal}信号'
            }

        # TRIX分析
        if 'TRIX' in df.columns:
            trix_latest = latest_data['TRIX']
            trix_signal = '中性'
            if trix_latest > 0:
                trix_signal = '看涨'
                signals_bullish += 1
            else:
                trix_signal = '看跌'
                signals_bearish += 1

            summary['indicator_analysis']['TRIX'] = {
                'signal': trix_signal,
                'interpretation': f'TRIX为{trix_latest:.6f}，显示{trix_signal}趋势'
            }

        # 综合判断
        if signals_bullish > signals_bearish:
            summary['overall_signal'] = '偏多'
            summary['suggestion'] = '技术指标整体显示看涨信号，建议考虑逢低布局或持有观望。'
        elif signals_bearish > signals_bullish:
            summary['overall_signal'] = '偏空'
            summary['suggestion'] = '技术指标整体显示看跌信号，建议谨慎操作或考虑减仓。'
        else:
            summary['overall_signal'] = '中性'
            summary['suggestion'] = '技术指标信号中性，建议观望为主，等待更明确的信号。'

        # 风险等级评估
        volatility_signals = 0
        if 'RSI14' in df.columns:
            rsi_latest = latest_data.get('RSI14', 50)
            if abs(rsi_latest - 50) > 30:
                volatility_signals += 1

        if 'ATR' in df.columns:
            atr_latest = latest_data['ATR']
            if not pd.isna(atr_latest) and atr_latest > 0:
                # 简单的ATR相对值评估
                if atr_latest > 0.02:  # 假设阈值
                    volatility_signals += 1

        if volatility_signals >= 2:
            summary['risk_level'] = '较高'
        elif volatility_signals == 1:
            summary['risk_level'] = '中等'
        else:
            summary['risk_level'] = '较低'

        return summary

    except Exception as e:
        st.error(f"生成技术分析摘要失败: {str(e)}")
        return None

def display_technical_analysis_summary(analysis_summary):
    """
    显示技术分析摘要

    Args:
        analysis_summary: 技术分析摘要字典
    """
    if analysis_summary is None:
        return

    try:
        # 主信号展示
        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric(
                "综合信号",
                analysis_summary['overall_signal'],
                help="基于多个技术指标的综合判断"
            )

        with col2:
            st.metric(
                "风险等级",
                analysis_summary['risk_level'],
                help="基于波动性和技术指标的风险评估"
            )

        with col3:
            # 计算看涨看跌指标数量
            bullish_count = sum(1 for analysis in analysis_summary['indicator_analysis'].values()
                              if '看涨' in analysis['signal'] or '超卖' in analysis['signal'])
            bearish_count = sum(1 for analysis in analysis_summary['indicator_analysis'].values()
                              if '看跌' in analysis['signal'] or '超买' in analysis['signal'])

            st.metric(
                "信号对比",
                f"多{bullish_count} 空{bearish_count}",
                help="看涨vs看跌指标数量对比"
            )

        # 投资建议
        st.info(f"💡 **投资建议**: {analysis_summary['suggestion']}")

        # 详细指标分析
        if analysis_summary['indicator_analysis']:
            st.subheader("📊 详细指标分析")

            for indicator, analysis in analysis_summary['indicator_analysis'].items():
                signal_color = {
                    '看涨': '🟢',
                    '看跌': '🔴',
                    '中性': '🟡',
                    '超买': '🔴',
                    '超卖': '🟢',
                    '上涨趋势': '🟢',
                    '下跌趋势': '🔴',
                    '震荡': '🟡'
                }.get(analysis['signal'], '⚪')

                st.write(f"{signal_color} **{indicator}**: {analysis['interpretation']}")

    except Exception as e:
        st.error(f"显示技术分析摘要失败: {str(e)}")