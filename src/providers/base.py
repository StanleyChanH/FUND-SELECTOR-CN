"""
DataProvider 抽象层（v2.0）

统一的数据源接口：无论数据来自 Tushare、用户自建 SQL 数据库还是本地缓存，
都通过相同的 fetch() 调用返回符合「规范数据集结构」的 DataFrame，
上层应用（Streamlit UI / 分析模块）不再与任何具体数据源耦合。
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

import pandas as pd


class ProviderError(Exception):
    """数据源配置或返回数据不符合规范时抛出。"""


@dataclass(frozen=True)
class DatasetSpec:
    """规范数据集定义：必选列、日期列、主键列。"""

    name: str
    required_columns: tuple[str, ...]
    date_column: str | None
    key_columns: tuple[str, ...]

    def register(self) -> "DatasetSpec":
        DATASET_REGISTRY[self.name] = self
        return self


DATASET_REGISTRY: dict[str, DatasetSpec] = {}

DatasetSpec(
    name="fund_nav",
    required_columns=("ts_code", "nav_date", "unit_nav"),
    date_column="nav_date",
    key_columns=("ts_code", "nav_date"),
).register()
DatasetSpec(
    name="fund_basic",
    required_columns=("ts_code", "name"),
    date_column=None,
    key_columns=("ts_code",),
).register()
DatasetSpec(
    name="fund_manager",
    required_columns=("ts_code", "name"),
    date_column=None,
    key_columns=("ts_code", "name", "begin_date"),
).register()
DatasetSpec(
    name="fund_share",
    required_columns=("ts_code", "trade_date", "fd_share"),
    date_column="trade_date",
    key_columns=("ts_code", "trade_date"),
).register()
DatasetSpec(
    name="fund_div",
    required_columns=("ts_code", "ex_date"),
    date_column="ex_date",
    key_columns=("ts_code", "ex_date"),
).register()
DatasetSpec(
    name="index_daily",
    required_columns=("ts_code", "trade_date", "close"),
    date_column="trade_date",
    key_columns=("ts_code", "trade_date"),
).register()


def normalize_date(series: pd.Series) -> pd.Series:
    """把日期列统一规范为 YYYYMMDD 字符串（兼容 datetime / ISO / 8 位数字串）。"""
    if pd.api.types.is_datetime64_any_dtype(series):
        return series.dt.strftime("%Y%m%d").astype("string")
    s = series.astype("string").str.strip()
    parsed = pd.to_datetime(s, errors="coerce", format="%Y%m%d")
    rest = parsed.isna()
    if rest.any():
        parsed.loc[rest] = pd.to_datetime(s[rest], errors="coerce")
    return parsed.dt.strftime("%Y%m%d").astype("string")


class DataProvider(ABC):
    """所有数据源的基类。

    子类只需实现 fetch()；基类负责按 DatasetSpec 校验必选列、
    规范日期格式并按日期升序排序。
    """

    name: str = "base"

    def __init__(self, datasets=None):
        if datasets is None:
            self._datasets = set(DATASET_REGISTRY)
        else:
            unknown = set(datasets) - set(DATASET_REGISTRY)
            if unknown:
                raise ProviderError(
                    self.name + ": unknown datasets " + str(sorted(unknown))
                )
            self._datasets = set(datasets)

    def supports(self, dataset: str) -> bool:
        return dataset in self._datasets

    def supported_datasets(self) -> list[str]:
        return sorted(self._datasets)

    @abstractmethod
    def fetch(self, dataset, *, code=None, start_date=None, end_date=None):
        """读取一个数据集，返回 DataFrame；无数据时返回 None 或空表。

        dataset: DATASET_REGISTRY 中的名称；code: 如 510300.SH；
        start_date/end_date: YYYYMMDD 字符串，含端点。
        """
        raise NotImplementedError

    def validate(self, dataset, df):
        """校验并规范返回数据：必选列齐全、日期列为 YYYYMMDD、按日期升序。"""
        spec = DATASET_REGISTRY.get(dataset)
        if spec is None:
            raise ProviderError("unknown dataset: " + str(dataset))
        if df is None or (hasattr(df, "empty") and df.empty):
            return df
        missing = [c for c in spec.required_columns if c not in df.columns]
        if missing:
            raise ProviderError(
                self.name + " 返回的 " + dataset + " 缺少必选列 " + str(missing)
                + "；现有列: " + str(list(df.columns)) + "。可用 column_map 重命名。"
            )
        df = df.copy()
        if spec.date_column and spec.date_column in df.columns:
            df[spec.date_column] = normalize_date(df[spec.date_column])
            df = df.dropna(subset=[spec.date_column])
            df = df.sort_values(spec.date_column).reset_index(drop=True)
        return df

    def __repr__(self):
        return self.name + ":datasets=" + str(self.supported_datasets())
