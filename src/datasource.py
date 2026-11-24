"""DataSource 统一门面（v2.0）。

读取链路：
    1. SQL 数据源（若配置）——用户自建库为实时真源，命中即返回（可选写穿缓存）
    2. 本地 Parquet 缓存——覆盖请求区间时直接返回，零网络
    3. 远端 Provider（默认 Tushare）——只补缺失区间，拉回后自动落地缓存

由此实现：Tushare 仅为「数据下载通道之一」，业务数据可完全来自自定义库。
"""

from __future__ import annotations
from datetime import datetime, timedelta

import pandas as pd

from .cache import ParquetCache
from .providers.base import DATASET_REGISTRY, DataProvider, ProviderError
from .providers.tushare_provider import TushareProvider


class DataSource:
    """组合多个 Provider 与本地缓存的统一数据入口。"""

    def __init__(self, sql_provider: DataProvider | None = None,
                 remote_provider: DataProvider | None = None,
                 cache: ParquetCache | None = None,
                 write_through: bool = True):
        self.sql = sql_provider
        self.remote = remote_provider
        self.cache = cache
        self.write_through = write_through

    # —— 构造 ————————————————————————————————————————
    @classmethod
    def from_config(cls, cfg: dict, token: str | None = None,
                    use_cache: bool = True) -> "DataSource":
        """从 load_config() 的结果构造。

        Args:
            cfg: 完整配置字典。
            token: 界面输入的 Tushare Token，优先于配置文件。
            use_cache: 界面开关，False 时完全禁用本地缓存。
        """
        ds_cfg = dict(cfg.get("datasource") or {})
        cache_cfg = cfg.get("cache") or {}
        sql_provider = None
        remote_provider = None
        kind = (ds_cfg.get("provider") or "tushare").lower()
        if kind == "sql":
            from .providers import SqlProvider

            sql_provider = SqlProvider(
                dsn=ds_cfg.get("dsn"),
                queries=ds_cfg.get("datasets") or {},
            )
        else:
            effective_token = token or ds_cfg.get("token")
            if effective_token:
                remote_provider = TushareProvider(token=effective_token)
        cache = None
        if use_cache and cache_cfg.get("enabled", True):
            cache = ParquetCache(cache_cfg.get("dir", ".fund_cache"))
        return cls(sql_provider=sql_provider, remote_provider=remote_provider,
                   cache=cache)

    # —— 读取 ————————————————————————————————————————
    def fetch(self, dataset: str, code: str | None = None,
              start_date: str | None = None,
              end_date: str | None = None) -> pd.DataFrame | None:
        if dataset not in DATASET_REGISTRY:
            raise ProviderError(f"未知数据集: {dataset}")

        # 1) 用户自建 SQL 库：实时真源
        if self.sql is not None and self.sql.supports(dataset):
            df = self.sql.fetch(dataset, code=code, start_date=start_date,
                                end_date=end_date)
            if df is not None and not df.empty:
                if self.write_through and self.cache is not None:
                    try:
                        self.cache.upsert(dataset, code or "_all", df)
                    except Exception:
                        pass  # 写穿失败不影响读取
                return df
            if df is not None:  # 空结果也视为有效响应，直接返回
                return df

        # 2) 本地缓存
        if self.cache is None:
            return self._fetch_remote(dataset, code, start_date, end_date)
        key = code or "_all"
        cached = self.cache.read(dataset, key, start_date, end_date)
        spec = DATASET_REGISTRY[dataset]
        need_fetch = True
        fetch_start = start_date
        if (cached is not None and not cached.empty and spec.date_column
                and start_date and end_date):
            cov = self.cache.coverage(dataset, key)
            if cov and cov[0] <= start_date and cov[1] >= end_date:
                need_fetch = False
            elif cov and cov[1] >= start_date:
                nxt = datetime.strptime(cov[1], "%Y%m%d") + timedelta(days=1)
                fetch_start = max(start_date, nxt.strftime("%Y%m%d"))
                if fetch_start > end_date:
                    need_fetch = False
        if need_fetch:
            df = self._fetch_remote(dataset, code, fetch_start, end_date)
            if df is not None and not df.empty:
                self.cache.upsert(dataset, key, df)
                cached = self.cache.read(dataset, key, start_date, end_date)
        return cached

    def _fetch_remote(self, dataset, code, start_date, end_date):
        if self.remote is None or not self.remote.supports(dataset):
            return None
        return self.remote.fetch(dataset, code=code, start_date=start_date,
                                 end_date=end_date)

    # —— 本地分析（数据落地后的离线玩法）———————————————
    def query_local(self, sql: str) -> pd.DataFrame:
        """用 DuckDB 直接 SQL 查询本地 Parquet 缓存（需安装 duckdb）。

        表名用 read_parquet 通配符引用缓存目录，例如：
            SELECT nav_date, unit_nav
            FROM read_parquet(<缓存目录>/fund_nav/*.parquet)
            WHERE ts_code = ?  ORDER BY nav_date
        """
        if self.cache is None:
            raise ProviderError("本地缓存未启用")
        try:
            import duckdb
        except ImportError as exc:
            raise ProviderError(
                "查询本地 Parquet 需要 duckdb：pip install duckdb"
            ) from exc
        return duckdb.sql(sql).to_df()

    def describe(self) -> dict:
        """当前数据源组合的描述信息，供 UI 展示。"""
        return {
            "sql": self.sql.name if self.sql else None,
            "remote": self.remote.name if self.remote else None,
            "cache": str(self.cache.root) if self.cache else None,
            "cache_stats": self.cache.stats() if self.cache else {},
        }
