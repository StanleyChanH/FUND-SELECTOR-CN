"""数据落地 CLI（v2.0）：把远端数据批量下载并持久化到本地。

用法示例：
    # 用界面同款配置，下载 510300.SH 近三年全部数据集
    python -m src.sync --codes 510300.SH

    # 指定区间 + 指定数据集，落地到自定义目录
    python -m src.sync --codes 510300.SH,000300.SH --datasets fund_nav,index_daily \
        --start 20200101 --end 20261124 --cache-dir data_lake

下载结果为 Parquet 文件，可用 DuckDB/pandas 直接离线分析：
    duckdb: SELECT * FROM read_parquet("data_lake/fund_nav/*.parquet") LIMIT 5
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime

from .config import load_config
from .datasource import DataSource
from .providers.base import DATASET_REGISTRY


DEFAULT_DATASETS = ("fund_nav", "fund_share", "fund_div", "fund_basic",
                    "fund_manager")


def sync_codes(ds: DataSource, codes: list[str], datasets: list[str],
               start_date: str, end_date: str) -> dict:
    """把指定代码 × 数据集的数据拉取并写入 DataSource 的缓存。"""
    report: dict[str, dict] = {}
    for code in codes:
        for dataset in datasets:
            spec = DATASET_REGISTRY[dataset]
            if spec.date_column:
                df = ds.fetch(dataset, code=code, start_date=start_date,
                              end_date=end_date)
            else:
                df = ds.fetch(dataset, code=code)
            rows = 0 if df is None else int(len(df))
            report.setdefault(code, {})[dataset] = rows
            print(f"[sync] {code} {dataset}: {rows} rows")
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m src.sync",
        description="把远端基金数据批量下载并落地为本地 Parquet",
    )
    parser.add_argument("--codes", required=True,
                        help="逗号分隔的代码列表，如 510300.SH,000300.SH")
    parser.add_argument("--datasets", default=",".join(DEFAULT_DATASETS),
                        help="逗号分隔的数据集，默认全部基础数据集")
    parser.add_argument("--start", default="20180101", help="起始日期 YYYYMMDD")
    parser.add_argument("--end", default=datetime.now().strftime("%Y%m%d"),
                        help="结束日期 YYYYMMDD，默认今天")
    parser.add_argument("--token", default=None, help="Tushare Token（或用环境变量/配置文件）")
    parser.add_argument("--config", default=None, help="配置文件路径（默认自动查找）")
    parser.add_argument("--cache-dir", default=None, help="覆盖配置中的缓存目录")
    args = parser.parse_args(argv)

    cfg = load_config(args.config)
    if args.cache_dir:
        cfg.setdefault("cache", {})["dir"] = args.cache_dir
        cfg["cache"]["enabled"] = True
    ds = DataSource.from_config(cfg, token=args.token, use_cache=True)
    if ds.remote is None and ds.sql is None:
        print("错误：配置里既没有 Tushare Token 也没有 SQL 数据源，无法下载。",
              file=sys.stderr)
        return 2
    if ds.cache is None:
        print("错误：缓存被禁用，数据无处落地。", file=sys.stderr)
        return 2

    codes = [c.strip() for c in args.codes.split(",") if c.strip()]
    datasets = [d.strip() for d in args.datasets.split(",") if d.strip()]
    bad = [d for d in datasets if d not in DATASET_REGISTRY]
    if bad:
        print(f"错误：未知数据集 {bad}，可用: {sorted(DATASET_REGISTRY)}",
              file=sys.stderr)
        return 2

    report = sync_codes(ds, codes, datasets, args.start, args.end)
    total = sum(sum(v.values()) for v in report.values())
    print(f"[sync] 完成：{len(codes)} 个代码，共落地 {total} 行，"
          f"目录 {ds.cache.root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
