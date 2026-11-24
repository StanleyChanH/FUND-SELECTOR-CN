"""SqlProvider 单元测试（SQLite 内存态文件库，无网络依赖）。"""
from __future__ import annotations

import pytest
from sqlalchemy import create_engine, text

from src.providers import SqlProvider
from src.providers.base import ProviderError


@pytest.fixture()
def sqlite_engine(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path}/funds.db", future=True)
    with engine.begin() as conn:
        conn.execute(text("CREATE TABLE my_nav (fund_code TEXT, d TEXT, v REAL, adj_v REAL)"))
        rows = [
            ("510300.SH", "2024-01-02", 1.01, 1.01),
            ("510300.SH", "2024-01-03", 1.02, 1.02),
            ("510300.SH", "2024-01-04", 1.03, 1.03),
        ]
        conn.execute(
            text("INSERT INTO my_nav (fund_code, d, v, adj_v) VALUES (:c, :d, :v, :a)"),
            [dict(c=c, d=d, v=v, a=a) for c, d, v, a in rows],
        )
    return engine


def _queries(with_map=True):
    q = {
        "fund_nav": {
            "query": ("SELECT fund_code, d, v, adj_v FROM my_nav "
                      "WHERE fund_code = :code AND d >= :start_date AND d <= :end_date "
                      "ORDER BY d"),
        }
    }
    if with_map:
        q["fund_nav"]["column_map"] = {"fund_code": "ts_code", "d": "nav_date",
                                       "v": "unit_nav", "adj_v": "adj_nav"}
    return q


def test_sql_provider_fetch_with_column_map(sqlite_engine):
    p = SqlProvider(engine=sqlite_engine, queries=_queries())
    df = p.fetch("fund_nav", code="510300.SH",
                 start_date="2024-01-01", end_date="2024-01-31")
    assert df is not None and len(df) == 3
    # ISO 日期被规范为 YYYYMMDD
    assert df.iloc[0]["nav_date"] == "20240102"
    assert list(df["unit_nav"]) == [1.01, 1.02, 1.03]


def test_sql_provider_unsupported_dataset_returns_none(sqlite_engine):
    p = SqlProvider(engine=sqlite_engine, queries=_queries())
    assert p.fetch("index_daily", code="000300.SH") is None


def test_sql_provider_missing_required_column_raises(sqlite_engine):
    queries = {
        "fund_nav": {
            "query": "SELECT fund_code, d FROM my_nav WHERE fund_code = :code",
            "column_map": {"fund_code": "ts_code", "d": "nav_date"},
        }
    }
    p = SqlProvider(engine=sqlite_engine, queries=queries)
    with pytest.raises(ProviderError, match="unit_nav"):
        p.fetch("fund_nav", code="510300.SH")


def test_sql_provider_empty_result(sqlite_engine):
    p = SqlProvider(engine=sqlite_engine, queries=_queries())
    df = p.fetch("fund_nav", code="159915.SZ",
                 start_date="2024-01-01", end_date="2024-01-31")
    assert df is not None and df.empty
