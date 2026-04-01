"""Utility function tests."""

from datetime import UTC, datetime, timedelta

from clarke.utils.ids import generate_episode_id, generate_id, generate_request_id
from clarke.utils.json import safe_json_dumps
from clarke.utils.time import ms_since, utc_now


def test_generate_request_id():
    rid = generate_request_id()
    assert rid.startswith("r_")
    assert len(rid) > 3


def test_generate_episode_id():
    eid = generate_episode_id()
    assert eid.startswith("ep_")


def test_generate_id_with_prefix():
    gid = generate_id("sub")
    assert gid.startswith("sub_")


def test_generate_id_no_prefix():
    gid = generate_id()
    assert "_" not in gid[:3]


def test_utc_now():
    now = utc_now()
    assert now.tzinfo is not None


def test_ms_since():
    start = datetime.now(UTC) - timedelta(milliseconds=100)
    elapsed = ms_since(start)
    assert elapsed >= 90  # allow some tolerance


def test_safe_json_dumps():
    result = safe_json_dumps({"time": datetime.now(UTC), "value": 42})
    assert '"value": 42' in result
