"""Tushare 数据源适配器：把 Tushare Pro API 包装为 DataProvider。

v2.0 起 Tushare 退化为「数据下载通道之一」——只负责在线拉数据，
不再与业务逻辑绑定；本地落地由 DataSource + ParquetCache 负责。
"""

from __future__ import annotations

import pandas as pd

from .base import DataProvider


class TushareProvider(DataProvider):
    """包装 tushare pro_api 对象。

    Args:
        pro: 已初始化的 tushare pro api 对象（优先）。
        token: 未提供 pro 时，用 token 现场初始化。
    """

    name = "tushare"

    def __init__(self, pro=None, token: str | None = None, datasets=None):
        super().__init__(datasets)
        if pro is None:
            import tushare as ts

            if not token:
                raise ValueError("TushareProvider 需要 pro 对象或 token")
            ts.set_token(token)
            pro = ts.pro_api()
        self._pro = pro

    def fetch(self, dataset, *, code=None, start_date=None, end_date=None):
        try:
            df = self._fetch(dataset, code, start_date, end_date)
        except Exception as exc:  # tushare 网络层抛出的各种异常
            raise ConnectionError(f"Tushare 获取 {dataset} 失败: {exc}") from exc
        return self.validate(dataset, df)

    def _fetch(self, dataset, code, start_date, end_date) -> pd.DataFrame:
        pro = self._pro
        if dataset == "fund_nav":
            df = pro.fund_nav(ts_code=code, start_date=start_date, end_date=end_date)
            if df is None or df.empty:
                # 场内基金没有 fund_nav 记录时回退到 fund_daily
                df = pro.fund_daily(ts_code=code, start_date=start_date, end_date=end_date)
            return df
        if dataset == "fund_basic":
            df = pro.fund_basic(market="E")
            if df is None or df.empty or not code:
                return df
            hit = df[df["ts_code"] == code]
            if hit.empty:
                hit = df[df["ts_code"].str.contains(code.split(".")[0], na=False)]
            return hit
        if dataset == "fund_manager":
            return pro.fund_manager(ts_code=code)
        if dataset == "fund_share":
            return pro.fund_share(ts_code=code, start_date=start_date, end_date=end_date)
        if dataset == "fund_div":
            return pro.fund_div(ts_code=code)
        if dataset == "index_daily":
            return pro.index_daily(ts_code=code, start_date=start_date, end_date=end_date)
        raise KeyError(f"TushareProvider 不支持数据集: {dataset}")
