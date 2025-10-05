"""
基于Tushare和Streamlit的交互式公募基金量化分析平台
主应用入口文件

依赖库: streamlit, pandas, numpy, plotly, tushare, pandas-ta
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
import tushare as ts

# 导入pandas-ta
import pandas_ta as ta

# 设置页面配置
st.set_page_config(
    page_title="基金量化分析平台",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 页面标题
st.title("📈 基金量化分析平台")
st.markdown("---")

# 导入自定义模块
from src.data_loader import (
    initialize_tushare, load_fund_data, load_fund_basic_info,
    load_fund_manager_info, load_fund_share_data, load_fund_div_data,
    load_benchmark_data, preprocess_fund_data
)
from src.indicators import (
    calculate_technical_indicators, calculate_performance_metrics,
    calculate_rolling_volatility, detect_golden_cross_death_cross
)
from src.visualization import (
    create_nav_chart, create_risk_charts, create_technical_indicator_charts,
    create_yearly_returns_chart, generate_technical_analysis_summary,
    display_technical_analysis_summary
)

def create_sidebar():
    """创建侧边栏控制面板"""
    st.sidebar.title("📊 控制面板")

    # Tushare Token输入
    token = st.sidebar.text_input(
        "Tushare Pro Token",
        type="password",
        help="请输入您的Tushare Pro API Token"
    )

    if not token:
        st.sidebar.warning("请输入Tushare Pro Token以继续")
        return None

    # 基金代码输入
    fund_code = st.sidebar.text_input(
        "基金代码",
        value="510300.SH",
        help="输入基金代码，例如: 510300.SH"
    )

    # 日期范围选择
    end_date = datetime.now()
    start_date = end_date - timedelta(days=3*365)  # 默认3年

    date_range = st.sidebar.date_input(
        "分析日期范围",
        value=(start_date, end_date),
        help="选择要分析的日期范围"
    )

    if len(date_range) == 2:
        start_date, end_date = date_range
        start_date_str = start_date.strftime('%Y%m%d')
        end_date_str = end_date.strftime('%Y%m%d')
    else:
        return None

    # 基准选择
    benchmark_options = {
        "沪深300": "000300.SH",
        "中证500": "000905.SH",
        "上证50": "000016.SH",
        "创业板指": "399006.SZ"
    }

    benchmark_name = st.sidebar.selectbox(
        "分析基准",
        list(benchmark_options.keys()),
        index=0
    )
    benchmark_code = benchmark_options[benchmark_name]

    # 基础技术分析参数
    st.sidebar.subheader("基础技术指标")

    short_ma = st.sidebar.slider(
        "短期移动平均线周期",
        min_value=5,
        max_value=50,
        value=20,
        step=5
    )

    long_ma = st.sidebar.slider(
        "长期移动平均线周期",
        min_value=20,
        max_value=200,
        value=60,
        step=10
    )

    rsi_period = st.sidebar.slider(
        "RSI计算周期",
        min_value=7,
        max_value=30,
        value=14,
        step=1
    )

    # 高级技术指标说明
    st.sidebar.subheader("高级技术指标")
    st.sidebar.info("将自动计算并显示所有技术指标：BOLL、MACD、KDJ、CCI、DMI、BBI、TRIX、ATR、OBV、MFI")

    return {
        'token': token,
        'fund_code': fund_code,
        'start_date': start_date_str,
        'end_date': end_date_str,
        'benchmark_code': benchmark_code,
        'benchmark_name': benchmark_name,
        'short_ma': short_ma,
        'long_ma': long_ma,
        'rsi_period': rsi_period
    }

def display_fund_overview(fund_basic_info, fund_manager_info, fund_share_data, fund_div_data, performance_metrics=None):
    """显示基金概览与核心信息"""
    st.header("📋 基金概览与核心信息")

    # 创建标签页
    tab1, tab2, tab3, tab4 = st.tabs(["核心业绩", "基本资料", "基金经理", "规模与分红"])

    with tab1:
        if performance_metrics:
            display_performance_metrics(performance_metrics)
        else:
            st.subheader("核心业绩指标")

    with tab2:
        st.subheader("基本资料")
        if fund_basic_info is not None:
            col1, col2 = st.columns(2)

            with col1:
                st.metric("基金全称", fund_basic_info.get('name', 'N/A'))
                st.metric("基金管理人", fund_basic_info.get('management', 'N/A'))
                st.metric("基金托管人", fund_basic_info.get('custodian', 'N/A'))

            with col2:
                st.metric("投资类型", fund_basic_info.get('type', 'N/A'))
                st.metric("成立日期", fund_basic_info.get('found_date', 'N/A'))
                st.metric("业绩比较基准", fund_basic_info.get('benchmark', 'N/A'))
        else:
            st.warning("无法获取基金基本信息")

    with tab3:
        st.subheader("基金经理信息")
        if fund_manager_info is not None and not fund_manager_info.empty:
            st.dataframe(fund_manager_info, use_container_width=True)
        else:
            st.warning("无法获取基金经理信息")

    with tab4:
        st.subheader("规模与分红")

        if fund_share_data is not None and not fund_share_data.empty:
            # 最新规模
            latest_share = fund_share_data.iloc[-1]
            fund_share_value = latest_share.get('fund_share', 'N/A')
            if fund_share_value != 'N/A' and pd.notna(fund_share_value):
                try:
                    fund_share_value = float(fund_share_value)
                    st.metric("最新基金份额", f"{fund_share_value:.2f}")
                except (ValueError, TypeError):
                    st.metric("最新基金份额", str(fund_share_value))
            else:
                st.metric("最新基金份额", "N/A")

            # 规模变化图表
            # 检查可用的日期列和份额列
            date_col = None
            share_col = None

            for col in ['ann_date', 'trade_date', 'end_date']:
                if col in fund_share_data.columns:
                    date_col = col
                    break

            for col in ['fd_share', 'fund_share']:
                if col in fund_share_data.columns:
                    share_col = col
                    break

            if date_col and share_col:
                fig = px.area(
                    fund_share_data,
                    x=date_col,
                    y=share_col,
                    title='基金份额历史变化'
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.warning("无法创建份额变化图表：缺少必要的列数据")
                st.write(f"可用列: {list(fund_share_data.columns)}")
        else:
            st.warning("无法获取基金份额数据")

        if fund_div_data is not None and not fund_div_data.empty:
            st.subheader("历史分红记录")
            st.dataframe(fund_div_data, use_container_width=True)
        else:
            st.warning("无法获取基金分红数据")

def display_performance_metrics(metrics):
    """显示业绩指标"""
    if metrics is None:
        return

    st.subheader("核心业绩指标")

    col1, col2, col3 = st.columns(3)
    col4, col5, col6 = st.columns(3)

    with col1:
        st.metric(
            "区间累计收益率",
            f"{metrics.get('total_return', 0):.2%}"
        )

    with col2:
        st.metric(
            "年化收益率",
            f"{metrics.get('annual_return', 0):.2%}"
        )

    with col3:
        st.metric(
            "年化波动率",
            f"{metrics.get('annual_volatility', 0):.2%}"
        )

    with col4:
        st.metric(
            "最大回撤",
            f"{metrics.get('max_drawdown', 0):.2%}"
        )

    with col5:
        st.metric(
            "夏普比率",
            f"{metrics.get('sharpe_ratio', 0):.3f}"
        )

    with col6:
        st.metric(
            "卡玛比率",
            f"{metrics.get('calmar_ratio', 0):.3f}"
        )

def main():
    """主函数"""
    # 创建侧边栏
    params = create_sidebar()

    if params is None:
        st.info("请在左侧控制面板中设置参数")
        return

    try:
        # 初始化Tushare API
        pro = initialize_tushare(params['token'])
        if pro is None:
            st.error("无法初始化Tushare API，请检查Token是否正确")
            return

        # 显示加载状态
        with st.spinner("正在加载数据..."):
            # 加载基金数据
            fund_raw = load_fund_data(pro, params['fund_code'], params['start_date'], params['end_date'])
            if fund_raw is None:
                st.error(f"无法获取基金 {params['fund_code']} 的数据")
                return

            # 预处理基金数据
            fund_data = preprocess_fund_data(fund_raw)
            if fund_data is None:
                st.error("数据预处理失败")
                return

            # 加载基准数据
            benchmark_raw = load_benchmark_data(
                pro, params['benchmark_code'],
                params['start_date'], params['end_date']
            )

            # 加载基金基本信息
            fund_basic_info = load_fund_basic_info(pro, params['fund_code'])
            fund_manager_info = load_fund_manager_info(pro, params['fund_code'])
            fund_share_data = load_fund_share_data(pro, params['fund_code'], params['start_date'], params['end_date'])
            fund_div_data = load_fund_div_data(pro, params['fund_code'])

            # 定义所有高级技术指标
            all_indicators = ["BOLL", "MACD", "KDJ", "CCI", "DMI", "BBI", "TRIX", "ATR", "OBV", "MFI"]

            # 计算技术指标
            fund_data = calculate_technical_indicators(
                fund_data,
                params['short_ma'],
                params['long_ma'],
                params['rsi_period'],
                all_indicators
            )

            # 计算滚动波动率
            fund_data['rolling_volatility'] = calculate_rolling_volatility(fund_data)

            # 计算业绩指标
            performance_metrics = calculate_performance_metrics(fund_data, benchmark_raw)

        # 显示基金概览
        display_fund_overview(fund_basic_info, fund_manager_info, fund_share_data, fund_div_data, performance_metrics)

        # 模块二：净值与通道指标可视化
        st.header("📈 净值与通道指标可视化")

        nav_chart = create_nav_chart(
            fund_data,
            benchmark_raw,
            show_ma=True,
            show_boll=True,  # 总是显示布林带
            short_ma=params['short_ma'],
            long_ma=params['long_ma']
        )

        if nav_chart:
            st.plotly_chart(nav_chart, use_container_width=True)

        # 模块三：风险与相对强弱分析
        st.header("⚠️ 风险与相对强弱分析")

        risk_charts = create_risk_charts(fund_data, params['rsi_period'])
        if risk_charts:
            st.plotly_chart(risk_charts, use_container_width=True)

        # 模块四：技术指标投资解读
        st.header("💡 技术指标投资解读")

        all_indicators = ["BOLL", "MACD", "KDJ", "CCI", "DMI", "BBI", "TRIX", "ATR", "OBV", "MFI"]
        analysis_summary = generate_technical_analysis_summary(fund_data, all_indicators)
        if analysis_summary:
            display_technical_analysis_summary(analysis_summary)

        # 模块五：高级技术指标分析
        st.header("🔬 高级技术指标分析")

        technical_charts = create_technical_indicator_charts(fund_data, all_indicators)
        for chart in technical_charts:
            st.plotly_chart(chart, use_container_width=True)

        # 模块六：年度收益表现
        st.header("📊 年度收益表现")

        yearly_chart = create_yearly_returns_chart(fund_data, benchmark_raw)
        if yearly_chart:
            st.plotly_chart(yearly_chart, use_container_width=True)

        st.success("分析完成！")

    except Exception as e:
        st.error(f"分析过程中发生错误: {str(e)}")
        st.exception(e)

if __name__ == "__main__":
    main()