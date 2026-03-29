"""Tests for the event dispatcher."""

from __future__ import annotations

import threading
import time
from unittest.mock import MagicMock

from ajazz_akp03e._events import (
    ButtonPress,
    ButtonRelease,
    Event,
    EventDispatcher,
    KnobTurn,
)


def _make_event(cls: type[Event], **kwargs: object) -> Event:
    return cls(device=MagicMock(), **kwargs)


class TestEventDispatcher:
    def test_dispatch_calls_callback(self) -> None:
        dispatcher = EventDispatcher()
        results: list[Event] = []
        dispatcher.on(ButtonPress, results.append)

        event = _make_event(ButtonPress, key=0)
        dispatcher.dispatch(event)
        dispatcher.shutdown()
        time.sleep(0.1)

        assert len(results) == 1
        assert results[0] is event

    def test_dispatch_filters_by_event_type(self) -> None:
        dispatcher = EventDispatcher()
        press_results: list[Event] = []
        release_results: list[Event] = []
        dispatcher.on(ButtonPress, press_results.append)
        dispatcher.on(ButtonRelease, release_results.append)

        dispatcher.dispatch(_make_event(ButtonPress, key=0))
        dispatcher.shutdown()
        time.sleep(0.1)

        assert len(press_results) == 1
        assert len(release_results) == 0

    def test_dispatch_filters_by_index(self) -> None:
        dispatcher = EventDispatcher()
        btn0: list[Event] = []
        btn1: list[Event] = []
        dispatcher.on(ButtonPress, btn0.append, index=0)
        dispatcher.on(ButtonPress, btn1.append, index=1)

        dispatcher.dispatch(_make_event(ButtonPress, key=0))
        dispatcher.dispatch(_make_event(ButtonPress, key=1))
        dispatcher.shutdown()
        time.sleep(0.1)

        assert len(btn0) == 1
        assert len(btn1) == 1

    def test_none_index_matches_all(self) -> None:
        dispatcher = EventDispatcher()
        results: list[Event] = []
        dispatcher.on(ButtonPress, results.append, index=None)

        dispatcher.dispatch(_make_event(ButtonPress, key=0))
        dispatcher.dispatch(_make_event(ButtonPress, key=5))
        dispatcher.shutdown()
        time.sleep(0.1)

        assert len(results) == 2

    def test_off_removes_callback(self) -> None:
        dispatcher = EventDispatcher()
        results: list[Event] = []

        def handler(e: Event) -> None:
            results.append(e)

        dispatcher.on(ButtonPress, handler)
        dispatcher.off(ButtonPress, handler)

        dispatcher.dispatch(_make_event(ButtonPress, key=0))
        dispatcher.shutdown()
        time.sleep(0.1)

        assert len(results) == 0

    def test_catch_all(self) -> None:
        dispatcher = EventDispatcher()
        results: list[Event] = []
        dispatcher.on_any(results.append)

        dispatcher.dispatch(_make_event(ButtonPress, key=0))
        dispatcher.dispatch(_make_event(KnobTurn, knob=1, direction=1))
        dispatcher.shutdown()
        time.sleep(0.1)

        assert len(results) == 2

    def test_callback_exception_is_caught(self) -> None:
        dispatcher = EventDispatcher()

        def bad_callback(event: Event) -> None:
            raise RuntimeError("boom")

        dispatcher.on(ButtonPress, bad_callback)

        # Should not raise — exception is logged and swallowed
        dispatcher.dispatch(_make_event(ButtonPress, key=0))
        dispatcher.shutdown()
        time.sleep(0.1)

    def test_multiple_callbacks_same_event(self) -> None:
        dispatcher = EventDispatcher()
        r1: list[Event] = []
        r2: list[Event] = []
        dispatcher.on(ButtonPress, r1.append)
        dispatcher.on(ButtonPress, r2.append)

        dispatcher.dispatch(_make_event(ButtonPress, key=0))
        dispatcher.shutdown()
        time.sleep(0.1)

        assert len(r1) == 1
        assert len(r2) == 1

    def test_thread_safe_registration(self) -> None:
        dispatcher = EventDispatcher()
        results: list[Event] = []
        errors: list[Exception] = []

        def register() -> None:
            try:
                for _ in range(100):
                    dispatcher.on(ButtonPress, results.append)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=register) for _ in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        dispatcher.shutdown()
        assert len(errors) == 0
