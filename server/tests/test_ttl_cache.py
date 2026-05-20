import time

from src.api.cache import TTLCache


def test_get_returns_none_for_missing_key() -> None:
    cache = TTLCache(ttl_seconds=60)
    assert cache.get("missing") is None


def test_set_then_get_returns_value() -> None:
    cache = TTLCache(ttl_seconds=60)
    cache.set("foo", {"a": 1, "b": [1, 2, 3]})
    assert cache.get("foo") == {"a": 1, "b": [1, 2, 3]}


def test_overwrite_replaces_value_and_resets_ttl() -> None:
    cache = TTLCache(ttl_seconds=60)
    cache.set("foo", 1)
    cache.set("foo", 2)
    assert cache.get("foo") == 2


def test_get_returns_none_after_ttl_expires() -> None:
    cache = TTLCache(ttl_seconds=0)
    cache.set("foo", "bar")
    time.sleep(0.01)
    assert cache.get("foo") is None


def test_expired_entry_is_removed_on_get() -> None:
    cache = TTLCache(ttl_seconds=0)
    cache.set("foo", "bar")
    time.sleep(0.01)
    cache.get("foo")
    assert "foo" not in cache._store
