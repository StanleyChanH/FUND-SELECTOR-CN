"""自定义 SQL 数据源（v2.0 核心新特性）。

用户在配置文件里为每个数据集写一条 SQL（支持 :code / :start_date / :end_date
三个绑定参数），SqlProvider 负责执行、按 column_map 重命名、
再按规范数据集结构校验。任何 SQLAlchemy 支持的数据库都可以接入：

    SQLite:      sqlite:///path/to/funds.db
    PostgreSQL:  postgresql+psycopg2://user:pass@host:5432/dbname
    MySQL:       mysql+pymysql://user:pass@host:3306/dbname
    ClickHouse:  clickhouse+native://host/dbname
    DuckDB:      duckdb:///path/to/funds.duckdb
"""

from __future__ import annotations

import pandas as pd

from .base import DataProvider, ProviderError


class SqlProvider(DataProvider):
    """基于用户自定义 SQL 查询的数据源。

    Args:
        dsn: SQLAlchemy 连接串。
        queries: {数据集: {"query": SQL, "column_map": {原始列: 规范列, ...}}}，
                 只需要配置用到的数据集，其余 fetch 时返回 None。
        engine: 已构造的 SQLAlchemy engine（测试/复用连接池时使用）。
    """

    name = "sql"

    def __init__(self, dsn: str | None = None, queries: dict | None = None,
                 engine=None, datasets=None):
        from sqlalchemy import create_engine

        self.queries = {k: dict(v) for k, v in (queries or {}).items()}
        if datasets is None:
            datasets = list(self.queries) or None
        super().__init__(datasets)
        if engine is not None:
            self._engine = engine
        elif dsn:
            self._engine = create_engine(dsn, future=True)
        else:
            raise ProviderError("SqlProvider 需要 dsn 或 engine")

    def fetch(self, dataset, *, code=None, start_date=None, end_date=None):
        if not self.supports(dataset):
            return None
        cfg = self.queries.get(dataset) or {}
        sql_text = cfg.get("query")
        if not sql_text:
            return None
        from sqlalchemy import text

        def _iso(d: str | None) -> str | None:
            return f"{d[:4]}-{d[4:6]}-{d[6:]}" if d and len(d) == 8 else d

        # 绑定参数：日期同时提供 YYYYMMDD 与 YYYY-MM-DD 两种格式，
        # 适配把日期存成 DATE / ISO 字符串的自建库，按需在 SQL 里选用。
        params: dict[str, str | None] = {
            "code": code,
            "start_date": start_date,
            "end_date": end_date,
            "start_date_iso": _iso(start_date),
            "end_date_iso": _iso(end_date),
        }
        with self._engine.connect() as conn:
            df = pd.read_sql(text(sql_text), conn, params=params)
        column_map = cfg.get("column_map") or {}
        if column_map:
            df = df.rename(columns=column_map)
        return self.validate(dataset, df)
