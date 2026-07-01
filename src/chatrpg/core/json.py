from __future__ import annotations

from typing import Any

import orjson


def dumps(value: Any) -> str:
    return orjson.dumps(value, option=orjson.OPT_SORT_KEYS).decode("utf-8")


def loads(raw: str | bytes) -> Any:
    return orjson.loads(raw)
