"""配置加载（v2.0）。

配置文件查找顺序：
    1. 显式传入的 path 参数
    2. 环境变量 FUND_SELECTOR_CONFIG 指向的文件
    3. 工作目录下的 config.yaml / config.yml / config.json
    4. 都不存在时使用内置默认值（纯 Tushare + 默认缓存）
"""

from __future__ import annotations

import json
import os
from pathlib import Path


DEFAULT_CONFIG: dict = {
    "datasource": {"provider": "tushare"},
    "cache": {"enabled": True, "dir": ".fund_cache"},
}

SEARCH_NAMES = ("config.yaml", "config.yml", "config.json")


def deep_merge(base: dict, override: dict) -> dict:
    out = dict(base)
    for k, v in (override or {}).items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = deep_merge(out[k], v)
        else:
            out[k] = v
    return out


def find_config_file(path: str | Path | None = None) -> Path | None:
    candidates = []
    if path:
        candidates.append(Path(path))
    env = os.environ.get("FUND_SELECTOR_CONFIG")
    if env:
        candidates.append(Path(env))
    else:
        candidates.extend(Path(n) for n in SEARCH_NAMES)
    for c in candidates:
        if c.is_file():
            return c
    return None


def load_config(path: str | Path | None = None) -> dict:
    """加载并合并配置；文件不存在时返回默认配置的副本。"""
    cfg_file = find_config_file(path)
    if cfg_file is None:
        return dict(DEFAULT_CONFIG)
    text = cfg_file.read_text(encoding="utf-8")
    if cfg_file.suffix == ".json":
        user_cfg = json.loads(text)
    else:
        try:
            import yaml
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError(
                "读取 YAML 配置需要 pyyaml，或改用 config.json"
            ) from exc
        user_cfg = yaml.safe_load(text) or {}
    return deep_merge(DEFAULT_CONFIG, user_cfg or {})


def validate_config(cfg: dict) -> list[str]:
    """返回配置问题列表（空列表 = 配置有效）。只做提示，不抛异常。"""
    problems: list[str] = []
    ds = cfg.get("datasource") or {}
    kind = (ds.get("provider") or "tushare").lower()
    if kind == "sql" and not ds.get("dsn"):
        problems.append("datasource.provider=sql 但未配置 dsn")
    if kind == "sql" and not (ds.get("datasets") or {}):
        problems.append("sql 数据源未配置任何 datasets 查询")
    if kind == "tushare" and not ds.get("token"):
        problems.append("tushare 数据源未配置 token（可在界面输入）")
    return problems
