"""本地数据落地：Parquet 缓存（v2.0）。

所有从远端（如 Tushare）下载的数据自动以 Parquet 格式落地到本地，
按「数据集/代码」一个文件组织，支持按主键 upsert 去重与增量合并。
DuckDB / pandas 均可直接查询这些 Parquet 文件（见 DataSource.query_local）。
"""

from __future__ import annotations

import re
from pathlib import Path

import pandas as pd

from .providers.base import DATASET_REGISTRY


class ParquetCache:
    """按 {root}/{dataset}/{code}.parquet 组织的本地缓存。"""

    def __init__(self, root: str | Path = ".fund_cache"):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    # —— 路径 ————————————————————————————————————————
    @staticmethod
    def _safe(code: str) -> str:
        return re.sub(r"[^A-Za-z0-9._-]", "_", str(code))

    def path_for(self, dataset: str, code: str) -> Path:
        folder = self.root / dataset
        folder.mkdir(parents=True, exist_ok=True)
        return folder / (self._safe(code) + ".parquet")

    # —— 读 ————————————————————————————————————————
    def read(self, dataset: str, code: str,
             start_date: str | None = None,
             end_date: str | None = None) -> pd.DataFrame | None:
        path = self.path_for(dataset, code)
        if not path.exists():
            return None
        df = pd.read_parquet(path)
        spec = DATASET_REGISTRY[dataset]
        if df.empty:
            return df
        col = spec.date_column
        if col and col in df.columns:
            if start_date:
                df = df[df[col].astype("string") >= str(start_date)]
            if end_date:
                df = df[df[col].astype("string") <= str(end_date)]
        return df.reset_index(drop=True) if hasattr(df, "reset_index") else df

    def coverage(self, dataset: str, code: str) -> tuple[str, str] | None:
        """返回缓存覆盖的日期范围 (min, max)；无日期列或无数据时返回 None。"""
        df = self.read(dataset, code)
        spec = DATASET_REGISTRY[dataset]
        if df is None or df.empty or not spec.date_column:
            return None
        col = spec.date_column
        if col not in df.columns:
            return None
        return (str(df[col].min()), str(df[col].max()))

    # —— 写 ————————————————————————————————————————
    def upsert(self, dataset: str, code: str, df: pd.DataFrame) -> pd.DataFrame:
        """按主键合并写入：新数据覆盖同主键旧行，按日期升序保存。"""
        if df is None or df.empty:
            existing = self.read(dataset, code)
            return existing if existing is not None else df
        spec = DATASET_REGISTRY[dataset]
        old = self.read(dataset, code)
        if old is not None and not old.empty:
            df = pd.concat([old, df], ignore_index=True)
        keys = [k for k in spec.key_columns if k in df.columns]
        if keys:
            df = df.drop_duplicates(subset=keys, keep="last")
        if spec.date_column and spec.date_column in df.columns:
            df = df.sort_values(spec.date_column)
        df = df.reset_index(drop=True)
        df.to_parquet(self.path_for(dataset, code), index=False)
        return df

    def stats(self) -> dict[str, dict]:
        """缓存概览，供 UI / 运维展示：每个数据集的文件数与总体积。"""
        out: dict[str, dict] = {}
        if not self.root.exists():
            return out
        for folder in sorted(self.root.iterdir()):
            if not folder.is_dir():
                continue
            files = list(folder.glob("*.parquet"))
            out[folder.name] = {
                "files": len(files),
                "bytes": sum(f.stat().st_size for f in files),
            }
        return out
