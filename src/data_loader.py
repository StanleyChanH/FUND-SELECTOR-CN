"""数据加载模块（v2.0 重构）。

对外函数签名与 v1 完全兼容：load_fund_data(source, code, start, end) 等。
source 现在接受三类对象：
    1. DataSource（推荐）——由 initialize_datasource() 构造
    2. v1 遗留的 tushare pro api 对象——自动包装为 TushareProvider
    3. 任意 DataProvider——自动配一个直读的 DataSource
"""

import streamlit as st
import pandas as pd
import tushare as ts

from .datasource import DataSource
from .providers.tushare_provider import TushareProvider


def initialize_tushare(token: str):
    """（v1 兼容）初始化 Tushare API。"""
    try:
        ts.set_token(token)
        return ts.pro_api()
    except Exception as e:
        st.error(f"Tushare API初始化失败: {str(e)}")
        return None


def initialize_datasource(config_path=None, token=None, use_cache=True):
    """（v2.0 推荐）初始化统一数据源。

    Args:
        config_path: 配置文件路径（config.yaml/json），None 时自动查找。
        token: Tushare Token（界面输入，优先于配置文件）。
        use_cache: 是否启用本地 Parquet 缓存。
    """
    from .config import load_config, validate_config

    cfg = load_config(config_path)
    for problem in validate_config(cfg):
        st.warning(f"配置提示: {problem}")
    ds = DataSource.from_config(cfg, token=token, use_cache=use_cache)
    if ds.sql is None and ds.remote is None and ds.cache is None:
        return None
    return ds


def _as_datasource(source) -> DataSource:
    """把任意Supported输入规范为 DataSource。"""
    if isinstance(source, DataSource):
        return source
    if source is None:
        raise ValueError("数据源未初始化")
    # v1 遗留：tushare pro api 对象（有 fund_nav / index_daily 等方法）
    if hasattr(source, "fund_nav") or hasattr(source, "index_daily"):
        return DataSource(remote_provider=TushareProvider(pro=source))
    # 裸 Provider
    from .providers.base import DataProvider

    if isinstance(source, DataProvider):
        return DataSource(remote_provider=source)
    raise TypeError(f"无法识别的数据源类型: {type(source)}")


@st.cache_data(ttl=3600, show_spinner=False)
def load_fund_data(_source, fund_code: str, start_date: str, end_date: str):
    """加载基金净值数据（SQL 库 → 本地缓存 → Tushare 下载并落地）。"""
    try:
        df = _as_datasource(_source).fetch(
            "fund_nav", code=fund_code, start_date=start_date, end_date=end_date)
        if df is None or df.empty:
            st.warning(f"未找到基金 {fund_code} 的净值数据")
            return None
        return df
    except Exception as e:
        st.error(f"加载基金数据失败: {str(e)}")
        return None


@st.cache_data(ttl=86400, show_spinner=False)
def load_fund_basic_info(_source, fund_code: str):
    """加载基金基本信息。"""
    try:
        df = _as_datasource(_source).fetch("fund_basic", code=fund_code)
        if df is None or df.empty:
            st.warning(f"未找到基金 {fund_code} 的基本信息")
            return None
        return df.iloc[0]
    except Exception as e:
        st.error(f"加载基金基本信息失败: {str(e)}")
        return None


@st.cache_data(ttl=86400, show_spinner=False)
def load_fund_manager_info(_source, fund_code: str):
    """加载基金经理信息。"""
    try:
        df = _as_datasource(_source).fetch("fund_manager", code=fund_code)
        if df is None or df.empty:
            st.warning(f"未找到基金 {fund_code} 的基金经理信息")
            return None
        return df
    except Exception as e:
        st.error(f"加载基金经理信息失败: {str(e)}")
        return None


@st.cache_data(ttl=3600, show_spinner=False)
def load_fund_share_data(_source, fund_code: str, start_date: str, end_date: str):
    """加载基金份额数据。"""
    try:
        df = _as_datasource(_source).fetch(
            "fund_share", code=fund_code, start_date=start_date, end_date=end_date)
        if df is None or df.empty:
            st.warning(f"未找到基金 {fund_code} 的份额数据")
            return None
        return df
    except Exception as e:
        st.error(f"加载份额数据失败: {str(e)}")
        return None


@st.cache_data(ttl=86400, show_spinner=False)
def load_fund_div_data(_source, fund_code: str):
    """加载基金分红数据。"""
    try:
        df = _as_datasource(_source).fetch("fund_div", code=fund_code)
        if df is None or df.empty:
            st.warning(f"未找到基金 {fund_code} 的分红数据")
            return None
        return df
    except Exception as e:
        st.error(f"加载分红数据失败: {str(e)}")
        return None


@st.cache_data(ttl=3600, show_spinner=False)
def load_benchmark_data(_source, benchmark_code: str, start_date: str, end_date: str):
    """加载基准指数数据。"""
    try:
        df = _as_datasource(_source).fetch(
            "index_daily", code=benchmark_code, start_date=start_date,
            end_date=end_date)
        if df is None or df.empty:
            st.warning(f"未找到基准指数 {benchmark_code} 的数据")
            return None
        return df
    except Exception as e:
        st.error(f"加载基准指数数据失败: {str(e)}")
        return None


def preprocess_fund_data(df_raw):
    """预处理基金数据（v1 逻辑保持不变）。"""
    if df_raw is None or df_raw.empty:
        return None

    try:
        if "ann_date" in df_raw.columns:
            df = df_raw.copy()
            df["date"] = pd.to_datetime(df_raw["ann_date"])
        elif "trade_date" in df_raw.columns:
            df = df_raw.copy()
            df["date"] = pd.to_datetime(df_raw["trade_date"])
        elif "nav_date" in df_raw.columns:  # v2.0: fund_nav 规范日期列
            df = df_raw.copy()
            df["date"] = pd.to_datetime(df_raw["nav_date"])
        else:
            st.error("数据中未找到有效的日期列")
            return None

        df = df.sort_values("date").reset_index(drop=True)

        nav_column = None
        for col in ["unit_nav", "adj_nav", "close"]:
            if col in df.columns:
                nav_column = col
                break

        if nav_column is None:
            st.error("数据中未找到净值列")
            return None

        df["nav"] = pd.to_numeric(df[nav_column], errors="coerce")
        df = df.dropna(subset=["nav", "date"])
        df["cum_nav"] = df["nav"] / df["nav"].iloc[0]
        return df

    except Exception as e:
        st.error(f"数据预处理失败: {str(e)}")
        return None
