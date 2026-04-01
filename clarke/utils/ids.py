"""ULID-based ID generators with entity-type prefixes."""

from ulid import ULID


def generate_request_id() -> str:
    return f"r_{ULID()}"


def generate_episode_id() -> str:
    return f"ep_{ULID()}"


def generate_trace_id() -> str:
    return f"tr_{ULID()}"


def generate_feedback_id() -> str:
    return f"fb_{ULID()}"


def generate_attribution_id() -> str:
    return f"at_{ULID()}"


def generate_weight_id() -> str:
    return f"sw_{ULID()}"


def generate_id(prefix: str = "") -> str:
    ulid = str(ULID())
    if prefix:
        return f"{prefix}_{ulid}"
    return ulid
