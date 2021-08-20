import sqlite3
import pytest
from time import sleep, perf_counter_ns
from sqlite_cache.sqlite_cache import Cache


def test_cache_creation():
    cache = Cache()
    assert cache.connection_string == ".cache:?mode=memory&cache=shared"


def test_cache_creation_double():
    cache1 = Cache()
    cache2 = Cache(filename=".cache2", in_memory=False)

    assert cache1.connection_string == ".cache:?mode=memory&cache=shared"
    assert cache2.connection_string == ".cache2"


def test_cache_method_failed():
    cache = Cache()
    try:
        cache.set(object(), object())  # noqa
    except sqlite3.InterfaceError:
        pass
    else:
        pytest.fail("Setting to key object() did not raise an error.")


def test_cache_set_and_get():
    cache = Cache()
    cache.set("foo", "bar")
    assert cache.get("foo") == "bar"


def test_cache_getitem_and_setitem():
    cache = Cache()
    cache["foo"] = "bar"
    assert cache["foo"] == "bar"


def test_cache_getitem_keyerror():
    cache = Cache()
    try:
        cache["foo"]
    except KeyError as e:
        assert str(e) == "'Key not in cache.'"
    else:
        pytest.fail("Accessing a key not in cache did not raise a KeyError.")


def test_cache_value_is_available():
    cache = Cache()
    cache.set("foo", "bar", 1)
    sleep(0.9)
    assert cache.get("foo") == "bar"


def test_cache_value_not_available():
    cache = Cache()
    cache.set("foo", "bar", 1)
    sleep(1)
    assert cache.get("foo") is None


def test_cache_add_and_get():
    cache = Cache()
    cache.add("foo", "bar")
    assert cache.get("foo") == "bar"


def test_cache_add_same_twice_and_get():
    cache = Cache()
    cache.add("foo", "bar")
    cache.add("foo", "baz")
    assert cache.get("foo") == "bar"


def test_cache_get_default_if_not_exists():
    cache = Cache()
    assert cache.get("foo", "bar") == "bar"


def test_cache_update():
    cache = Cache()
    cache.set("foo", "bar")
    cache.update("foo", "baz")
    assert cache.get("foo") == "baz"


def test_cache_delete():
    cache = Cache()
    cache.set("foo", "bar")
    cache.delete("foo")
    assert cache.get("foo") is None


def test_cache_get_or_set():
    cache = Cache()
    cache.get_or_set("foo", "bar")
    assert cache.get_or_set("foo", None) == "bar"


def test_cache_get_or_set__expired():
    cache = Cache()
    cache.get_or_set("foo", "bar", 1)
    sleep(1)
    assert cache.get_or_set("foo", None) is None


def test_cache_get_many():
    cache = Cache()
    cache.set("foo", "bar")
    cache.set("one", "two")
    assert cache.get_many(["foo", "one"]) == {"foo": "bar", "one": "two"}


def test_cache_get_many__nothing():
    cache = Cache()
    cache.set("foo", "bar")
    cache.set("one", "two")
    assert cache.get_many(["three", "four"]) == {}


def test_cache_get_many__expired():
    cache = Cache()
    cache.set("foo", "bar", 1)
    cache.set("one", "two", 1)
    sleep(1)
    assert cache.get_many(["foo", "one"]) == {}


def test_cache_set_many():
    cache = Cache()
    cache.set_many({"foo": "bar", "one": "two"})
    assert cache.get_many(["foo", "one"]) == {"foo": "bar", "one": "two"}


def test_cache_add_many():
    cache = Cache()
    cache.set("foo", "bar")
    cache.add_many({"foo": "baz", "one": "two"})
    assert cache.get_many(["foo", "one"]) == {"foo": "bar", "one": "two"}


def test_cache_update_many():
    cache = Cache()
    cache.set_many({"foo": "bar", "one": "two"})
    cache.update_many({"foo": "baz", "three": "four"})
    assert cache.get_many(["foo", "one"]) == {"foo": "baz", "one": "two"}
    assert cache.get("three") is None


def test_cache_delte_many():
    cache = Cache()
    cache.set_many({"foo": "bar", "one": "two"})
    cache.delete_many(["foo", "one"])
    assert cache.get_many(["foo", "one"]) == {}


def test_cache_touch():
    cache = Cache()
    cache.set("foo", "bar", 1)
    cache.touch("foo", 2)
    sleep(1)
    assert cache.get("foo") == "bar"


def test_cache_touch_many():
    cache = Cache()
    cache.set_many({"foo": "bar", "one": "two"}, 1)
    cache.touch_many(["foo", "one"])
    sleep(1)
    assert cache.get_many(["foo", "one"]) == {"foo": "bar", "one": "two"}


def test_cache_clear():
    cache = Cache()
    cache.set("foo", "bar")
    cache.clear()
    assert cache.get("foo") is None


def test_cache_incr():
    cache = Cache()
    cache.set("foo", 1)
    cache.incr("foo")
    assert cache.get("foo") == 2


def test_cache_incr__not_exists():
    cache = Cache()
    try:
        cache.incr("foo")
    except ValueError as e:
        assert str(e) == "Nonexistent or expired cache key."
    else:
        pytest.fail("Incrementing a nonexistent key did not raise an error.")


def test_cache_incr__not_a_number():
    cache = Cache()
    cache.set("foo", "bar")
    try:
        cache.incr("foo")
    except ValueError as e:
        assert str(e) == "Value is not a number."
    else:
        pytest.fail("Incrementing a non-number key did not raise an error.")


def test_cache_decr():
    cache = Cache()
    cache.set("foo", 1)
    cache.decr("foo")
    assert cache.get("foo") == 0


def test_cache_decr__not_exists():
    cache = Cache()
    try:
        cache.decr("foo")
    except ValueError as e:
        assert str(e) == "Nonexistent or expired cache key."
    else:
        pytest.fail("Decrementing a nonexistent key did not raise an error.")


def test_cache_decr__not_a_number():
    cache = Cache()
    cache.set("foo", "bar")
    try:
        cache.decr("foo")
    except ValueError as e:
        assert str(e) == "Value is not a number."
    else:
        pytest.fail("Decrementing a non-number key did not raise an error.")


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

    print(f"\n\n Cache creation: {creation} μs\n")
    print(f" Average of {times:_}:")
    print("--------------------------------------------")
    print(f" Set: {set_:.01f}μs - Min: {set_min:.01f}μs - Max: {set_max:.01f}μs")
    print(f" Get: {get_:.01f}μs - Min: {get_min:.01f}μs - Max: {get_max:.01f}μs")
    print(f" Del: {del_:.01f}μs - Min: {del_min:.01f}μs - Max: {del_max:.01f}μs")
    print("--------------------------------------------")
