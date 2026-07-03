from __future__ import annotations

import uuid
from datetime import UTC, datetime


def new_id(prefix: str) -> str:
    suffix = uuid.uuid7() if hasattr(uuid, "uuid7") else uuid.uuid4()
    return f"{prefix}_{suffix}"


def utc_now_iso() -> str:
    return datetime.now(UTC).isoformat()
