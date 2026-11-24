"""sync CLI 核心逻辑测试（FakeProvider，无网络）。"""
from __future__ import annotations


from src.cache import ParquetCache
from src.datasource import DataSource
from src.sync import sync_codes
from tests.test_datasource import FakeRemote


def test_sync_codes_writes_cache(tmp_path):
    remote = FakeRemote()
    cache = ParquetCache(tmp_path / "lake")
    ds = DataSource(remote_provider=remote, cache=cache)
    report = sync_codes(ds, ["510300.SH"], ["fund_nav"],
                        "20240101", "20240103")
    assert report["510300.SH"]["fund_nav"] == 3
    assert cache.coverage("fund_nav", "510300.SH") == ("20240101", "20240103")


def test_sync_codes_no_data_dataset(tmp_path):
    ds = DataSource(remote_provider=FakeRemote(),
                    cache=ParquetCache(tmp_path / "lake"))
    report = sync_codes(ds, ["510300.SH"], ["fund_share"],
                        "20240101", "20240103")
    assert report["510300.SH"]["fund_share"] == 0
