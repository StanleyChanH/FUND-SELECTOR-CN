"""DataProvider 工厂与注册表。"""

from __future__ import annotations

from .base import DATASET_REGISTRY, DataProvider, DatasetSpec, ProviderError, normalize_date
from .sql_provider import SqlProvider
from .tushare_provider import TushareProvider


def create_provider(cfg: dict) -> DataProvider:
    """根据配置字典构造 Provider。

    cfg 形如（对应 config.yaml 的 datasource 段）：
        {"provider": "sql", "dsn": "...", "datasets": {...}}
        {"provider": "tushare", "token": "..."}
    """
    kind = (cfg.get("provider") or cfg.get("type") or "tushare").lower()
    if kind == "tushare":
        return TushareProvider(token=cfg.get("token"))
    if kind == "sql":
        if not cfg.get("dsn") and not cfg.get("engine"):
            raise ProviderError("sql 数据源缺少 dsn")
        return SqlProvider(
            dsn=cfg.get("dsn"),
            queries=cfg.get("datasets") or {},
            engine=cfg.get("engine"),
        )
    raise ProviderError(f"未知数据源类型: {kind}（可用: tushare / sql）")


__all__ = [
    "DATASET_REGISTRY",
    "DataProvider",
    "DatasetSpec",
    "ProviderError",
    "SqlProvider",
    "TushareProvider",
    "create_provider",
    "normalize_date",
]
