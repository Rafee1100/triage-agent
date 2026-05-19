import time
from pathlib import Path

from src.github.cache import DiskCache


def test_get_returns_none_for_missing_key(tmp_path: Path) -> None:
    cache = DiskCache(cache_dir=str(tmp_path))
    assert cache.get("missing") is None


def test_set_then_get_round_trips_value(tmp_path: Path) -> None:
    cache = DiskCache(cache_dir=str(tmp_path))
    cache.set("foo", {"bar": 1, "baz": [1, 2, 3]})
    assert cache.get("foo") == {"bar": 1, "baz": [1, 2, 3]}


def test_get_returns_none_after_ttl_expires(tmp_path: Path) -> None:
    cache = DiskCache(cache_dir=str(tmp_path))
    cache.set("foo", {"bar": 1}, ttl_seconds=0)
    time.sleep(0.01)
    assert cache.get("foo") is None


def test_init_does_not_touch_filesystem(tmp_path: Path) -> None:
    target = tmp_path / "lazy"
    DiskCache(cache_dir=str(target))
    assert not target.exists()
