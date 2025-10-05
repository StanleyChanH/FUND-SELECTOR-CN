"""
技术指标计算模块
负责计算各种技术分析指标和业绩指标
"""

import streamlit as st
import pandas as pd
import numpy as np

# 导入pandas-ta
import pandas_ta as ta
HAS_PANDAS_TA = True

def calculate_technical_indicators(df, short_ma=20, long_ma=60, rsi_period=14, selected_indicators=None):
    """
    计算技术指标

    Args:
        df: 包含净值数据的DataFrame
        short_ma: 短期移动平均线周期
        long_ma: 长期移动平均线周期
        rsi_period: RSI计算周期
        selected_indicators: 用户选择的高级指标列表

    Returns:
        DataFrame: 包含技术指标的数据
    """
    if df is None or df.empty:
        return None

    try:
        df_indicators = df.copy()

        # 基础技术指标
        # 移动平均线
        df_indicators[f'MA{short_ma}'] = ta.sma(df_indicators['nav'], length=short_ma)
        df_indicators[f'MA{long_ma}'] = ta.sma(df_indicators['nav'], length=long_ma)
        df_indicators[f'RSI{rsi_period}'] = ta.rsi(df_indicators['nav'], length=rsi_period)

        # 高级技术指标（根据用户选择计算）
        if selected_indicators:
            if 'BOLL' in selected_indicators:
                boll = ta.bbands(df_indicators['nav'], length=20, std=2)
                df_indicators['BOLL_UPPER'] = boll['BBU_20_2.0_2.0']
                df_indicators['BOLL_MIDDLE'] = boll['BBM_20_2.0_2.0']
                df_indicators['BOLL_LOWER'] = boll['BBL_20_2.0_2.0']

            if 'MACD' in selected_indicators:
                macd = ta.macd(df_indicators['nav'])
                df_indicators['MACD_DIF'] = macd['MACD_12_26_9']
                df_indicators['MACD_DEA'] = macd['MACDs_12_26_9']
                df_indicators['MACD_HIST'] = macd['MACDh_12_26_9']

            if 'KDJ' in selected_indicators:
                kdj = ta.stoch(df_indicators['nav'], df_indicators['nav'], df_indicators['nav'], k=9, d=3, smooth_k=3)
                df_indicators['KDJ_K'] = kdj['STOCHk_9_3_3']
                df_indicators['KDJ_D'] = kdj['STOCHd_9_3_3']
                df_indicators['KDJ_J'] = 3 * df_indicators['KDJ_K'] - 2 * df_indicators['KDJ_D']

            if 'CCI' in selected_indicators:
                cci = ta.cci(df_indicators['nav'], df_indicators['nav'], df_indicators['nav'], length=20)
                df_indicators['CCI'] = cci

            if 'DMI' in selected_indicators:
                dmi = ta.adx(df_indicators['nav'], df_indicators['nav'], df_indicators['nav'], length=14)
                df_indicators['DMI_PLUS'] = dmi['DMP_14']
                df_indicators['DMI_MINUS'] = dmi['DMN_14']
                df_indicators['DMI_ADX'] = dmi['ADX_14']

            if 'BBI' in selected_indicators:
                ma3 = ta.sma(df_indicators['nav'], length=3)
                ma6 = ta.sma(df_indicators['nav'], length=6)
                ma12 = ta.sma(df_indicators['nav'], length=12)
                ma24 = ta.sma(df_indicators['nav'], length=24)
                df_indicators['BBI'] = (ma3 + ma6 + ma12 + ma24) / 4

            if 'TRIX' in selected_indicators:
                trix = ta.trix(df_indicators['nav'], length=12)
                # TRIX返回DataFrame，包含TRIX和信号线
                if isinstance(trix, pd.DataFrame):
                    df_indicators['TRIX'] = trix['TRIX_12_9']
                    df_indicators['TRIX_SIGNAL'] = trix['TRIXs_12_9']
                else:
                    df_indicators['TRIX'] = trix

            if 'ATR' in selected_indicators:
                df_indicators['ATR'] = ta.atr(df_indicators['nav'], df_indicators['nav'], df_indicators['nav'], length=14)

            if 'OBV' in selected_indicators:
                # OBV需要成交量数据，如果没有则创建虚拟成交量
                if 'volume' not in df_indicators.columns:
                    # 创建虚拟成交量数据
                    volume_data = pd.Series(1000000, index=df_indicators.index)  # 固定成交量
                else:
                    volume_data = df_indicators['volume']
                df_indicators['OBV'] = ta.obv(df_indicators['nav'], volume_data)

            if 'MFI' in selected_indicators:
                # MFI需要高低价和成交量数据
                if 'volume' not in df_indicators.columns:
                    volume_data = pd.Series(1000000, index=df_indicators.index)
                else:
                    volume_data = df_indicators['volume']
                mfi = ta.mfi(df_indicators['nav'], df_indicators['nav'], df_indicators['nav'], volume_data, length=14)
                df_indicators['MFI'] = mfi

        return df_indicators

    except Exception as e:
        st.error(f"技术指标计算失败: {str(e)}")
        return df

def calculate_performance_metrics(df, benchmark_df=None):
    """
    计算业绩指标

    Args:
        df: 基金数据DataFrame
        benchmark_df: 基准数据DataFrame（可选）

    Returns:
        dict: 业绩指标字典
    """
    if df is None or df.empty:
        return None

    try:
        metrics = {}

        # 基础收益率计算
        returns = df['nav'].pct_change().dropna()
        cum_returns = (df['cum_nav'].iloc[-1] / df['cum_nav'].iloc[0]) - 1

        # 年化收益率
        trading_days = len(df)
        years = trading_days / 252  # 假设一年252个交易日
        annual_return = (1 + cum_returns) ** (1 / years) - 1

        # 年化波动率
        annual_volatility = returns.std() * np.sqrt(252)

        # 最大回撤
        rolling_max = df['cum_nav'].expanding().max()
        drawdown = (df['cum_nav'] - rolling_max) / rolling_max
        max_drawdown = drawdown.min()

        # 夏普比率（假设无风险利率为3%）
        risk_free_rate = 0.03
        sharpe_ratio = (annual_return - risk_free_rate) / annual_volatility if annual_volatility > 0 else 0

        # 卡玛比率
        calmar_ratio = annual_return / abs(max_drawdown) if max_drawdown != 0 else 0

        # 基本指标
        metrics['total_return'] = cum_returns
        metrics['annual_return'] = annual_return
        metrics['annual_volatility'] = annual_volatility
        metrics['max_drawdown'] = max_drawdown
        metrics['sharpe_ratio'] = sharpe_ratio
        metrics['calmar_ratio'] = calmar_ratio

        # 如果有基准数据，计算相对指标
        if benchmark_df is not None and not benchmark_df.empty:
            benchmark_returns = benchmark_df['close'].pct_change().dropna()

            # 对齐日期
            common_dates = df['date'].isin(benchmark_df['trade_date'])
            fund_aligned = df[common_dates].reset_index(drop=True)
            benchmark_aligned = benchmark_df[benchmark_df['trade_date'].isin(fund_aligned['date'])].reset_index(drop=True)

            if len(fund_aligned) > 0 and len(benchmark_aligned) > 0:
                # 超额收益率
                excess_returns = fund_aligned['nav'].pct_change().dropna() - benchmark_aligned['close'].pct_change().dropna()

                # 信息比率
                tracking_error = excess_returns.std() * np.sqrt(252)
                information_ratio = excess_returns.mean() * np.sqrt(252) / tracking_error if tracking_error > 0 else 0

                # Beta
                if len(fund_aligned) == len(benchmark_aligned):
                    covariance = np.cov(fund_aligned['nav'].pct_change().dropna(),
                                      benchmark_aligned['close'].pct_change().dropna())[0][1]
                    benchmark_variance = np.var(benchmark_aligned['close'].pct_change().dropna())
                    beta = covariance / benchmark_variance if benchmark_variance > 0 else 1

                    metrics['beta'] = beta
                    metrics['information_ratio'] = information_ratio
                    metrics['tracking_error'] = tracking_error

        return metrics

    except Exception as e:
        st.error(f"业绩指标计算失败: {str(e)}")
        return None

def calculate_rolling_volatility(df, window=60):
    """
    计算滚动波动率

    Args:
        df: 基金数据DataFrame
        window: 滚动窗口

    Returns:
        Series: 滚动波动率
    """
    if df is None or df.empty:
        return None

    try:
        returns = df['nav'].pct_change().dropna()
        rolling_vol = returns.rolling(window=window).std() * np.sqrt(252)
        return rolling_vol

    except Exception as e:
        st.error(f"滚动波动率计算失败: {str(e)}")
        return None

def detect_golden_cross_death_cross(df, short_ma=20, long_ma=60):
    """
    检测金叉和死叉信号

    Args:
        df: 包含移动平均线的DataFrame
        short_ma: 短期均线周期
        long_ma: 长期均线周期

    Returns:
        tuple: (金叉日期列表, 死叉日期列表)
    """
    if df is None or df.empty:
        return [], []

    try:
        short_col = f'MA{short_ma}'
        long_col = f'MA{long_ma}'

        if short_col not in df.columns or long_col not in df.columns:
            return [], []

        # 计算金叉死叉信号
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

    except Exception as e:
        st.error(f"金叉死叉检测失败: {str(e)}")
        return [], []