"""
数据加载模块
负责从Tushare API获取基金相关数据
"""

import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import tushare as ts
import time

def initialize_tushare(token: str):
    """初始化Tushare API"""
    try:
        ts.set_token(token)
        pro = ts.pro_api()
        return pro
    except Exception as e:
        st.error(f"Tushare API初始化失败: {str(e)}")
        return None

@st.cache_data(ttl=3600)
def load_fund_data(_pro, fund_code: str, start_date: str, end_date: str):
    """
    加载基金净值数据

    Args:
        _pro: Tushare Pro API对象
        fund_code: 基金代码
        start_date: 开始日期
        end_date: 结束日期

    Returns:
        DataFrame: 基金净值数据
    """
    try:
        # 转换基金代码格式 (510300.SH -> 510300)
        ts_code = fund_code

        # 获取基金净值数据
        df_nav = _pro.fund_nav(ts_code=ts_code, start_date=start_date, end_date=end_date)

        if df_nav.empty:
            st.warning(f"未找到基金 {fund_code} 的净值数据，尝试使用fund_daily接口")
            # 尝试使用fund_daily接口
            df_daily = _pro.fund_daily(ts_code=ts_code, start_date=start_date, end_date=end_date)
            if df_daily.empty:
                st.error(f"无法获取基金 {fund_code} 的任何数据")
                return None
            return df_daily

        return df_nav

    except Exception as e:
        st.error(f"加载基金数据失败: {str(e)}")
        return None

@st.cache_data(ttl=86400)  # 基本信息缓存24小时
def load_fund_basic_info(_pro, fund_code: str):
    """
    加载基金基本信息

    Args:
        _pro: Tushare Pro API对象
        fund_code: 基金代码

    Returns:
        DataFrame: 基金基本信息
    """
    try:
        df_basic = _pro.fund_basic(market='E')
        # 转换基金代码格式
        fund_code_clean = fund_code.split('.')[0]

        # 查找对应基金
        fund_info = df_basic[df_basic['ts_code'] == fund_code]

        if fund_info.empty:
            # 尝试其他匹配方式
            fund_info = df_basic[df_basic['ts_code'].str.contains(fund_code_clean)]

        if fund_info.empty:
            st.warning(f"未找到基金 {fund_code} 的基本信息")
            return None

        return fund_info.iloc[0]

    except Exception as e:
        st.error(f"加载基金基本信息失败: {str(e)}")
        return None

@st.cache_data(ttl=86400)
def load_fund_manager_info(_pro, fund_code: str):
    """
    加载基金经理信息

    Args:
        _pro: Tushare Pro API对象
        fund_code: 基金代码

    Returns:
        DataFrame: 基金经理信息
    """
    try:
        fund_code_clean = fund_code.split('.')[0]
        df_manager = _pro.fund_manager(ts_code=fund_code)

        if df_manager.empty:
            st.warning(f"未找到基金 {fund_code} 的基金经理信息")
            return None

        return df_manager

    except Exception as e:
        st.error(f"加载基金经理信息失败: {str(e)}")
        return None

@st.cache_data(ttl=3600)
def load_fund_share_data(_pro, fund_code: str, start_date: str, end_date: str):
    """
    加载基金份额数据

    Args:
        _pro: Tushare Pro API对象
        fund_code: 基金代码
        start_date: 开始日期
        end_date: 结束日期

    Returns:
        DataFrame: 基金份额数据
    """
    try:
        df_share = _pro.fund_share(ts_code=fund_code, start_date=start_date, end_date=end_date)

        if df_share.empty:
            st.warning(f"未找到基金 {fund_code} 的份额数据")
            return None

        return df_share

    except Exception as e:
        st.error(f"加载基金份额数据失败: {str(e)}")
        return None

@st.cache_data(ttl=86400)
def load_fund_div_data(_pro, fund_code: str):
    """
    加载基金分红数据

    Args:
        _pro: Tushare Pro API对象
        fund_code: 基金代码

    Returns:
        DataFrame: 基金分红数据
    """
    try:
        df_div = _pro.fund_div(ts_code=fund_code)

        if df_div.empty:
            st.warning(f"未找到基金 {fund_code} 的分红数据")
            return None

        return df_div

    except Exception as e:
        st.error(f"加载基金分红数据失败: {str(e)}")
        return None

@st.cache_data(ttl=3600)
def load_benchmark_data(_pro, benchmark_code: str, start_date: str, end_date: str):
    """
    加载基准指数数据

    Args:
        _pro: Tushare Pro API对象
        benchmark_code: 基准指数代码
        start_date: 开始日期
        end_date: 结束日期

    Returns:
        DataFrame: 基准指数数据
    """
    try:
        df_index = _pro.index_daily(ts_code=benchmark_code, start_date=start_date, end_date=end_date)

        if df_index.empty:
            st.warning(f"未找到基准指数 {benchmark_code} 的数据")
            return None

        return df_index

    except Exception as e:
        st.error(f"加载基准指数数据失败: {str(e)}")
        return None

def preprocess_fund_data(df_raw):
    """
    预处理基金数据

    Args:
        df_raw: 原始数据DataFrame

    Returns:
        DataFrame: 预处理后的数据
    """
    if df_raw is None or df_raw.empty:
        return None

    try:
        # 确保日期列存在并转换为datetime
        if 'ann_date' in df_raw.columns:
            df = df_raw.copy()
            df['date'] = pd.to_datetime(df['ann_date'])
        elif 'trade_date' in df_raw.columns:
            df = df_raw.copy()
            df['date'] = pd.to_datetime(df['trade_date'])
        else:
            st.error("数据中未找到有效的日期列")
            return None

        # 按日期排序
        df = df.sort_values('date').reset_index(drop=True)

        # 处理净值列
        nav_column = None
        for col in ['unit_nav', 'adj_nav', 'close']:
            if col in df.columns:
                nav_column = col
                break

        if nav_column is None:
            st.error("数据中未找到净值列")
            return None

        df['nav'] = pd.to_numeric(df[nav_column], errors='coerce')

        # 删除空值
        df = df.dropna(subset=['nav', 'date'])

        # 计算累计净值（归一化到1）
        df['cum_nav'] = df['nav'] / df['nav'].iloc[0]

        return df

    except Exception as e:
        st.error(f"数据预处理失败: {str(e)}")
        return None