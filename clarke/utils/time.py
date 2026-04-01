"""Time utilities."""

from datetime import UTC, datetime


def utc_now() -> datetime:
    return datetime.now(UTC)


def ms_since(start: datetime) -> int:
    delta = utc_now() - start
    return int(delta.total_seconds() * 1000)
