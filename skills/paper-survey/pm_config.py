#!/usr/bin/env python3
"""Standalone config loader for paper-survey skill. No external dependencies."""

import copy
import json
import sys
from functools import lru_cache
from pathlib import Path


DEFAULT_CONFIG = {
    "paths": {
        "obsidian_vault": "~/ObsidianVault",
        "survey_folder": "论文調研",
    },
    "survey": {
        "max_papers_per_search": 100,
        "max_papers_final": 15,
        "min_citation_count": 5,
        "year_range_default": 5,
        "include_preprints": False,
        "language": "zh-TW",
        "semantic_scholar_api_key": "",
    },
    "automation": {
        "git_commit": False,
        "git_push": False,
    },
}


def _deep_merge(base: dict, override: dict) -> dict:
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(base.get(key), dict):
            _deep_merge(base[key], value)
        else:
            base[key] = value
    return base


@lru_cache(maxsize=1)
def load_config() -> dict:
    config = copy.deepcopy(DEFAULT_CONFIG)
    config_dir = Path(__file__).resolve().parent

    for filename in ("pm-config.json", "pm-config.local.json"):
        p = config_dir / filename
        if not p.exists():
            continue
        with p.open("r", encoding="utf-8") as f:
            loaded = json.load(f)
        if isinstance(loaded, dict):
            _deep_merge(config, loaded)

    return config


@lru_cache(maxsize=1)
def load_venue_db() -> dict:
    config_dir = Path(__file__).resolve().parent
    venue_path = config_dir / "venue_db.json"
    with venue_path.open("r", encoding="utf-8") as f:
        db = json.load(f)

    cfg = load_config()
    overrides = cfg.get("venue_overrides")
    if isinstance(overrides, dict):
        _deep_merge(db, overrides)

    return db


def _expand(p: str) -> Path:
    return Path(p).expanduser()


def obsidian_vault_path() -> Path:
    return _expand(load_config()["paths"]["obsidian_vault"])


def survey_dir() -> Path:
    return obsidian_vault_path() / load_config()["paths"]["survey_folder"]


def survey_config() -> dict:
    return load_config()["survey"]


def automation_config() -> dict:
    cfg = load_config()["automation"]
    if cfg.get("git_push") and not cfg.get("git_commit"):
        cfg = copy.deepcopy(cfg)
        cfg["git_push"] = False
    return cfg


def temp_dir() -> Path:
    if sys.platform == "win32":
        d = Path.home() / "tmp"
    else:
        d = Path("/tmp")
    d.mkdir(parents=True, exist_ok=True)
    return d


def temp_file_path(name: str) -> Path:
    return temp_dir() / name


if __name__ == "__main__":
    import pprint
    pprint.pprint(load_config())
    print(f"\nVault: {obsidian_vault_path()}")
    print(f"Survey dir: {survey_dir()}")
