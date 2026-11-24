"""ParquetCache 单元测试。"""
from __future__ import annotations

import pandas as pd

from src.cache import ParquetCache


def _nav_df(dates, values, code="510300.SH"):
    return pd.DataFrame({
        "ts_code": [code] * len(dates),
        "nav_date": dates,
        "unit_nav": values,
    })


def test_upsert_and_read(tmp_path):
    cache = ParquetCache(tmp_path / "c")
    df = _nav_df(["20240101", "20240102"], [1.0, 1.1])
    out = cache.upsert("fund_nav", "510300.SH", df)
    assert len(out) == 2
    got = cache.read("fund_nav", "510300.SH")
    assert list(got["unit_nav"]) == [1.0, 1.1]


def test_upsert_dedupes_and_keeps_latest(tmp_path):
    cache = ParquetCache(tmp_path / "c")
    cache.upsert("fund_nav", "510300.SH", _nav_df(["20240101"], [1.0]))
    # 同一主键新值应覆盖旧值
    cache.upsert("fund_nav", "510300.SH", _nav_df(["20240101", "20240103"], [2.0, 1.3]))
    got = cache.read("fund_nav", "510300.SH")
    assert len(got) == 2
    assert got.loc[got.nav_date == "20240101", "unit_nav"].iloc[0] == 2.0


def test_read_date_range_filter(tmp_path):
    cache = ParquetCache(tmp_path / "c")
    cache.upsert("fund_nav", "510300.SH",
                 _nav_df(["20240101", "20240102", "20240103"], [1.0, 1.1, 1.2]))
    got = cache.read("fund_nav", "510300.SH",
                     start_date="20240102", end_date="20240102")
    assert list(got["nav_date"]) == ["20240102"]


def test_coverage(tmp_path):
    cache = ParquetCache(tmp_path / "c")
    assert cache.coverage("fund_nav", "510300.SH") is None
    cache.upsert("fund_nav", "510300.SH",
                 _nav_df(["20240102", "20240105"], [1.0, 1.1]))
    assert cache.coverage("fund_nav", "510300.SH") == ("20240102", "20240105")


def test_stats(tmp_path):
    cache = ParquetCache(tmp_path / "c")
    cache.upsert("fund_nav", "510300.SH", _nav_df(["20240101"], [1.0]))
    stats = cache.stats()
    assert stats["fund_nav"]["files"] == 1
    assert stats["fund_nav"]["bytes"] > 0
