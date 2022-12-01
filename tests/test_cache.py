import sqlite3
from time import perf_counter_ns, sleep

import pytest

from sqlite3_cache import Cache


def test_cache_creation(cache, freezer):
    freezer.move_to("2022-01-01T00:00:00+00:00")
    assert cache.connection_string == ".cache:?mode=memory&cache=shared"


def test_cache_method_failed(cache, freezer):
    freezer.move_to("2022-01-01T00:00:00+00:00")
    try:
        cache.set(object(), object())  # noqa
    except sqlite3.Error:
        pass
    else:
        pytest.fail("Setting to key object() did not raise an error.")


def test_cache_set_and_get(cache, freezer):
    freezer.move_to("2022-01-01T00:00:00+00:00")
    cache.set("foo", "bar", timeout=1)
    assert cache.get("foo") == "bar"


def test_cache_getitem_and_setitem(cache, freezer):
    freezer.move_to("2022-01-01T00:00:00+00:00")
    cache["foo"] = "bar"
    assert cache["foo"] == "bar"


def test_cache_getitem_key_error(cache, freezer):
    freezer.move_to("2022-01-01T00:00:00+00:00")
    try:
        cache["foo"]
    except KeyError as e:
        assert str(e) == "'Key not in cache.'"
    else:
        pytest.fail("Accessing a key not in cache did not raise a KeyError.")


def test_cache_delitem(cache, freezer):
    freezer.move_to("2022-01-01T00:00:00+00:00")
    cache["foo"] = "bar"
    del cache["foo"]
    assert cache.get("foo") is None


def test_cache_context_manager(cache, freezer):
    freezer.move_to("2022-01-01T00:00:00+00:00")
    cache["foo"] = "bar"
    cache.close()
    with Cache() as cache:
        value = cache["foo"]
    assert value == "bar"


def test_cache_contains(cache):
    cache["foo"] = "bar"
    assert ("foo" in cache) is True


def test_cache_value_is_available(cache, freezer):
    freezer.move_to("2022-01-01T00:00:00+00:00")
    cache.set("foo", "bar", timeout=2)
    freezer.move_to("2022-01-01T00:00:01+00:00")
    assert cache.get("foo") == "bar"


def test_cache_value_not_available(cache, freezer):
    freezer.move_to("2022-01-01T00:00:00+00:00")
    cache.set("foo", "bar", timeout=1)
    freezer.move_to("2022-01-01T00:00:01+00:00")
    assert cache.get("foo") is None


def test_cache_value_not_set(cache, freezer):
    freezer.move_to("2022-01-01T00:00:00+00:00")
    assert cache.get("foo") is None


def test_cache_value_does_not_expire(cache, freezer):
    freezer.move_to("2022-01-01T00:00:00+00:00")
    cache.set("foo", "bar", timeout=-1)
    freezer.move_to("9999-01-01T00:00:00+00:00")
    assert cache.get("foo") == "bar"


def test_cache_add_and_get(cache, freezer):
    freezer.move_to("2022-01-01T00:00:00+00:00")
    cache.add("foo", "bar", timeout=1)
    assert cache.get("foo") == "bar"


def test_cache_add_same_twice_and_get(cache):
    cache.add("foo", "bar", timeout=1)
    cache.add("foo", "baz", timeout=1)
    assert cache.get("foo") == "bar"


def test_cache_add_same_twice_and_get__has_expired(cache):
    cache.add("foo", "bar", timeout=1)
    cache.add("foo", "baz", timeout=1)
    assert cache.get("foo") == "bar"
    sleep(1.1)
    cache.add("foo", "baz", timeout=1)
    assert cache.get("foo") == "baz"


def test_cache_add_same_twice_and_get__non_expiring(cache, freezer):
    freezer.move_to("2022-01-01T00:00:00+00:00")
    cache.add("foo", "bar", timeout=-1)
    cache.add("foo", "baz", timeout=-1)
    assert cache.get("foo") == "bar"


def test_cache_get_default_if_not_exists(cache, freezer):
    freezer.move_to("2022-01-01T00:00:00+00:00")
    assert cache.get("foo", "bar") == "bar"


def test_cache_update(cache):
    cache.set("foo", "bar", timeout=10)
    cache.update("foo", "baz")
    assert cache.get("foo") == "baz"


def test_cache_update__non_expiring(cache, freezer):
    freezer.move_to("2022-01-01T00:00:00+00:00")
    cache.set("foo", "bar", timeout=-1)
    cache.update("foo", "baz")
    assert cache.get("foo") == "baz"


def test_cache_update__does_not_exist(cache, freezer):
    freezer.move_to("2022-01-01T00:00:00+00:00")
    cache.update("foo", "baz")
    assert cache.get("foo") is None


def test_cache_delete(cache, freezer):
    freezer.move_to("2022-01-01T00:00:00+00:00")
    cache.set("foo", "bar", timeout=1)
    cache.delete("foo")
    assert cache.get("foo") is None


def test_cache_delete__nothing(cache, freezer):
    freezer.move_to("2022-01-01T00:00:00+00:00")
    cache.delete("foo")
    assert cache.get("foo") is None


def test_cache_get_or_set(cache, freezer):
    freezer.move_to("2022-01-01T00:00:00+00:00")
    cache.set("foo", "bar", timeout=2)
    freezer.move_to("2022-01-01T00:00:01+00:00")
    assert cache.get_or_set("foo", None) == "bar"


def test_cache_get_or_set__expired(cache, freezer):
    freezer.move_to("2022-01-01T00:00:00+00:00")
    cache.set("foo", "bar", timeout=1)
    freezer.move_to("2022-01-01T00:00:01+00:00")
    assert cache.get_or_set("foo", None) is None


def test_cache_get_many(cache, freezer):
    freezer.move_to("2022-01-01T00:00:00+00:00")
    cache.set("foo", "bar", timeout=2)
    cache.set("one", "two", timeout=2)
    freezer.move_to("2022-01-01T00:00:01+00:00")
    assert cache.get_many(["foo", "one"]) == {"foo": "bar", "one": "two"}


def test_cache_get_many__expired(cache, freezer):
    freezer.move_to("2022-01-01T00:00:00+00:00")
    cache.set("foo", "bar", timeout=1)
    cache.set("one", "two", timeout=1)
    freezer.move_to("2022-01-01T00:00:01+00:00")
    assert cache.get_many(["foo", "one"]) == {}


def test_cache_get_many__nothing(cache, freezer):
    freezer.move_to("2022-01-01T00:00:00+00:00")
    cache.set("foo", "bar", timeout=1)
    cache.set("one", "two", timeout=1)
    assert cache.get_many(["three", "four"]) == {}


def test_cache_set_many(cache, freezer):
    freezer.move_to("2022-01-01T00:00:00+00:00")
    cache.set_many({"foo": "bar", "one": "two"}, timeout=2)
    freezer.move_to("2022-01-01T00:00:01+00:00")
    assert cache.get_many(["foo", "one"]) == {"foo": "bar", "one": "two"}


def test_cache_set_many__expired(cache, freezer):
    freezer.move_to("2022-01-01T00:00:00+00:00")
    cache.set_many({"foo": "bar", "one": "two"}, timeout=1)
    freezer.move_to("2022-01-01T00:00:01+00:00")
    assert cache.get_many(["foo", "one"]) == {}


def test_cache_add_many(cache):
    cache.set("foo", "bar", timeout=10)
    cache.add_many({"foo": "baz", "one": "two"}, timeout=10)
    assert cache.get_many(["foo", "one"]) == {"foo": "bar", "one": "two"}


def test_cache_add_many__expired(cache):
    cache.set("foo", "bar", timeout=1)
    sleep(1.1)
    cache.add_many({"foo": "baz", "one": "two"}, timeout=1)
    assert cache.get_many(["foo", "one"]) == {"foo": "baz", "one": "two"}


def test_cache_update_many(cache):
    cache.set_many({"foo": "bar", "one": "two"}, timeout=10)
    cache.update_many({"foo": "baz", "three": "four"})
    assert cache.get_many(["foo", "one"]) == {"foo": "baz", "one": "two"}
    assert cache.get("three") is None


def test_cache_delete_many(cache, freezer):
    freezer.move_to("2022-01-01T00:00:00+00:00")
    cache.set_many({"foo": "bar", "one": "two"}, timeout=1)
    cache.delete_many(["foo", "one"])
    assert cache.get_many(["foo", "one"]) == {}


def test_cache_delete_many__nothing(cache, freezer):
    freezer.move_to("2022-01-01T00:00:00+00:00")
    cache.delete_many(["foo", "one"])
    assert cache.get_many(["foo", "one"]) == {}


def test_cache_touch(cache):
    cache.set("foo", "bar", timeout=1)
    cache.touch("foo", timeout=3)
    sleep(1.1)
    assert cache.get("foo") == "bar"


def test_cache_touch__make_expiring(cache):
    cache.set("foo", "bar", timeout=-10)
    cache.touch("foo", timeout=1)
    sleep(1.1)
    assert cache.get("foo") is None


def test_cache_touch__non_expiring(cache):
    cache.set("foo", "bar", timeout=1)
    cache.touch("foo", timeout=-1)
    sleep(1.1)
    assert cache.get("foo") == "bar"


def test_cache_touch_many(cache):
    cache.set_many({"foo": "bar", "one": "two"}, timeout=1)
    cache.touch_many(["foo", "one"], timeout=3)
    sleep(1.1)
    assert cache.get_many(["foo", "one"]) == {"foo": "bar", "one": "two"}


def test_cache_clear(cache, freezer):
    freezer.move_to("2022-01-01T00:00:00+00:00")
    cache.set("foo", "bar", timeout=1)
    cache.clear()
    assert cache.get("foo") is None


def test_cache_incr(cache):
    cache.set("foo", 1, timeout=10)
    assert cache.incr("foo") == 2


def test_cache_incr__not_exists(cache):
    try:
        cache.incr("foo")
    except ValueError as e:
        assert str(e) == "Nonexistent or expired cache key."
    else:
        pytest.fail("Incrementing a nonexistent key did not raise an error.")


def test_cache_incr__not_a_number(cache):
    cache.set("foo", "bar", timeout=10)
    try:
        cache.incr("foo")
    except ValueError as e:
        assert str(e) == "Value is not a number."
    else:
        pytest.fail("Incrementing a non-number key did not raise an error.")


def test_cache_decr(cache):
    cache.set("foo", 1, timeout=10)
    assert cache.decr("foo") == 0


def test_cache_decr__not_exists(cache):
    try:
        cache.decr("foo")
    except ValueError as e:
        assert str(e) == "Nonexistent or expired cache key."
    else:
        pytest.fail("Decrementing a nonexistent key did not raise an error.")


def test_cache_decr__not_a_number(cache):
    cache.set("foo", "bar", timeout=10)
    try:
        cache.decr("foo")
    except ValueError as e:
        assert str(e) == "Value is not a number."
    else:
        pytest.fail("Decrementing a non-number key did not raise an error.")


def test_cache_memoize(cache, freezer):
    freezer.move_to("2022-01-01T00:00:00+00:00")

    @cache.memoize()
    def func(a: int, b: int) -> int:
        return a + b

    value1 = func(1, 2)
    value2 = func(1, 3)
    assert value1 != value2

    value3 = None
    try:
        value3 = func(1, 2)
    except Exception as e:
        pytest.fail(str(e))

    assert value1 == value3


def test_cache_ttl(cache, freezer):
    freezer.move_to("2022-01-01T00:00:00+00:00")
    cache.set("foo", "bar", timeout=10)
    assert cache.ttl("foo") == 10


def test_cache_ttl__not_exists(cache, freezer):
    freezer.move_to("2022-01-01T00:00:00+00:00")
    assert cache.ttl("foo") == -2


def test_cache_ttl__expired(cache, freezer):
    freezer.move_to("2022-01-01T00:00:00+00:00")
    cache.set("foo", "bar", timeout=1)
    freezer.move_to("2022-01-01T00:00:01+00:00")
    assert cache.ttl("foo") == -2


def test_cache_ttl__non_expiring(cache, freezer):
    freezer.move_to("2022-01-01T00:00:00+00:00")
    cache.set("foo", "bar", timeout=-1)
    freezer.move_to("9999-01-01T00:00:00+00:00")
    assert cache.ttl("foo") == -1


def test_cache_ttl_many(cache, freezer):
    freezer.move_to("2022-01-01T00:00:00+00:00")
    cache.set("foo", "bar", timeout=1)
    cache.set("one", "two", timeout=2)
    assert cache.ttl_many(["foo", "one"]) == {"foo": 1, "one": 2}


def test_cache_ttl_many__not_exists(cache, freezer):
    freezer.move_to("2022-01-01T00:00:00+00:00")
    assert cache.ttl_many(["foo", "one"]) == {"foo": -2, "one": -2}


def test_cache_ttl_many__non_expiring(cache, freezer):
    freezer.move_to("2022-01-01T00:00:00+00:00")
    cache.set("foo", "bar", timeout=-1)
    cache.set("one", "two", timeout=-2)
    assert cache.ttl_many(["foo", "one"]) == {"foo": -1, "one": -1}


def test_cache_ttl_many__expired(cache, freezer):
    freezer.move_to("2022-01-01T00:00:00+00:00")
    cache.set("foo", "bar", timeout=1)
    cache.set("one", "two", timeout=1)
    freezer.move_to("2022-01-01T00:00:01+00:00")
    assert cache.ttl_many(["foo", "one"]) == {"foo": -2, "one": -2}


@pytest.mark.skip("this is a benchmark")
def test_speed():
    start = perf_counter_ns()
    cache = Cache()
    interval1 = perf_counter_ns()

    set_ = []
    get_ = []
    del_ = []

    times = 10_000
    for _ in range(times):
        interval2 = perf_counter_ns()
        cache.set("foo", "bar")
        interval3 = perf_counter_ns()
        value = cache.get("foo")
        interval4 = perf_counter_ns()
        cache.delete("foo")
        interval5 = perf_counter_ns()

        set_.append(interval3 - interval2)
        get_.append(interval4 - interval3)
        del_.append(interval5 - interval4)

    set_min = min(set_) / 1000
    get_min = min(get_) / 1000
    del_min = min(del_) / 1000

    set_max = max(set_) / 1000
    get_max = max(get_) / 1000
    del_max = max(del_) / 1000

    creation = (interval1 - start) / 1000
    set_ = sum(set_) / len(set_) / 1000
    get_ = sum(get_) / len(get_) / 1000
    del_ = sum(del_) / len(del_) / 1000

    print(f"\n\n Cache creation: {creation} us\n")
    print(f" Average of {times:_}:")
    print("--------------------------------------------")
    print(f" Set: {set_:.01f}us - Min: {set_min:.01f}us - Max: {set_max:.01f}us")
    print(f" Get: {get_:.01f}us - Min: {get_min:.01f}us - Max: {get_max:.01f}us")
    print(f" Del: {del_:.01f}us - Min: {del_min:.01f}us - Max: {del_max:.01f}us")
    print("--------------------------------------------")
