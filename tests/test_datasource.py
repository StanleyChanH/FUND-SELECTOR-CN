"""DataSource 读取链路与 config 加载测试（FakeProvider，无网络）。"""
from __future__ import annotations

import pandas as pd

from src.cache import ParquetCache
from src.config import deep_merge, load_config, validate_config
from src.datasource import DataSource
from src.providers.base import DataProvider


class FakeRemote(DataProvider):
    name = "fake_remote"

    def __init__(self, datasets=None):
        super().__init__(datasets)
        self.calls: list[tuple] = []

    def fetch(self, dataset, *, code=None, start_date=None, end_date=None):
        self.calls.append((dataset, code, start_date, end_date))
        if dataset == "fund_nav":
            dates = ["20240101", "20240102", "20240103"]
            if start_date:
                dates = [d for d in dates if d >= start_date]
            if end_date:
                dates = [d for d in dates if d <= end_date]
            return pd.DataFrame({
                "ts_code": [code] * len(dates),
                "nav_date": dates,
                "unit_nav": [1.0 + 0.1 * i for i in range(len(dates))],
            })
        return None


def test_fetch_hits_remote_then_serves_from_cache(tmp_path):
    remote = FakeRemote()
    ds = DataSource(remote_provider=remote, cache=ParquetCache(tmp_path))
    df1 = ds.fetch("fund_nav", code="510300.SH",
                   start_date="20240101", end_date="20240103")
    assert len(df1) == 3
    assert len(remote.calls) == 1
    # 第二次同区间：直接命中缓存，远端零调用
    df2 = ds.fetch("fund_nav", code="510300.SH",
                   start_date="20240101", end_date="20240103")
    assert len(df2) == 3
    assert len(remote.calls) == 1


def test_partial_coverage_triggers_gap_fetch(tmp_path):
    remote = FakeRemote()
    ds = DataSource(remote_provider=remote, cache=ParquetCache(tmp_path))
    ds.fetch("fund_nav", code="510300.SH",
             start_date="20240101", end_date="20240102")
    assert len(remote.calls) == 1
    # 扩大区间：缓存覆盖到 0102，只应补拉 0103 起的缺口
    ds.fetch("fund_nav", code="510300.SH",
             start_date="20240101", end_date="20240103")
    assert len(remote.calls) == 2
    assert remote.calls[1][2] == "20240103"  # gap start


def test_sql_provider_takes_priority(tmp_path):
    class FakeSql(FakeRemote):
        name = "fake_sql"

    sql = FakeSql()
    remote = FakeRemote()
    ds = DataSource(sql_provider=sql, remote_provider=remote,
                    cache=ParquetCache(tmp_path))
    df = ds.fetch("fund_nav", code="510300.SH",
                  start_date="20240101", end_date="20240103")
    assert len(df) == 3
    assert len(sql.calls) == 1
    assert len(remote.calls) == 0  # SQL 命中后不走远端


def test_cache_only_returns_none_when_empty(tmp_path):
    ds = DataSource(remote_provider=None, cache=ParquetCache(tmp_path))
    assert ds.fetch("fund_nav", code="510300.SH",
                    start_date="20240101", end_date="20240103") is None


def test_describe(tmp_path):
    ds = DataSource(remote_provider=FakeRemote(), cache=ParquetCache(tmp_path))
    info = ds.describe()
    assert info["remote"] == "fake_remote"
    assert info["sql"] is None
    assert "fund_nav" in info["cache_stats"] or info["cache_stats"] == {}


def test_config_default_when_missing(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("FUND_SELECTOR_CONFIG", raising=False)
    cfg = load_config()
    assert cfg["datasource"]["provider"] == "tushare"
    assert cfg["cache"]["enabled"] is True


def test_config_deep_merge():
    cfg = deep_merge(
        {"datasource": {"provider": "tushare", "token": "a"}, "cache": {"enabled": True}},
        {"datasource": {"provider": "sql", "dsn": "sqlite:///x.db"}},
    )
    assert cfg["datasource"]["provider"] == "sql"
    assert cfg["datasource"]["token"] == "a"  # 未覆盖的键保留
    assert cfg["cache"]["enabled"] is True


def test_validate_config_reports_sql_problems():
    problems = validate_config({"datasource": {"provider": "sql"}})
    assert any("dsn" in p for p in problems)
    assert any("datasets" in p for p in problems)
