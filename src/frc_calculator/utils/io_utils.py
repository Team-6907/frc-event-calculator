from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


def ensure_parent_dir(filepath: str | os.PathLike) -> None:
    Path(filepath).parent.mkdir(parents=True, exist_ok=True)


def load_json_data(filepath: str):
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def write_json_data(obj: Any, filepath: str) -> None:
    ensure_parent_dir(filepath)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(obj, f, sort_keys=True, indent=4)

