"""Event types and dispatcher for device input handling."""

from __future__ import annotations

import logging
import threading
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ajazz_akp03e._device import AKP03E

logger = logging.getLogger(__name__)


@dataclass
class Event:
    """Base event from the device."""

    device: AKP03E


@dataclass
class ButtonPress(Event):
    """A button was pressed down."""

    key: int = 0


@dataclass
class ButtonRelease(Event):
    """A button was released."""

    key: int = 0


@dataclass
class KnobTurn(Event):
    """A rotary encoder was twisted."""

    knob: int = 0
    direction: int = 0  # -1 = CCW, +1 = CW


@dataclass
class KnobPress(Event):
    """A rotary encoder was pressed down."""

    knob: int = 0


@dataclass
class KnobRelease(Event):
    """A rotary encoder was released."""

    knob: int = 0


# Callback type: any callable that accepts an Event subclass
EventCallback = Callable[[Any], None]


@dataclass
class _Registration:
    """A single callback registration with optional index filter."""

    callback: EventCallback
    index: int | None = None  # None = all indices


class EventDispatcher:
    """Thread-safe event callback registry and dispatcher."""

    def __init__(self, max_workers: int = 4) -> None:
        self._registrations: dict[type[Event], list[_Registration]] = {}
        self._catch_all: list[EventCallback] = []
        self._lock = threading.Lock()
        self._executor = ThreadPoolExecutor(max_workers=max_workers)

    def on(
        self,
        event_type: type[Event],
        callback: EventCallback,
        *,
        index: int | None = None,
    ) -> None:
        """Register a callback for a specific event type.

        Args:
            event_type: The event class to listen for.
            callback: Function to call when the event fires.
            index: Optional key/knob index filter. None matches all.
        """
        with self._lock:
            regs = self._registrations.setdefault(event_type, [])
            regs.append(_Registration(callback=callback, index=index))

    def on_any(self, callback: EventCallback) -> None:
        """Register a catch-all callback for every event."""
        with self._lock:
            self._catch_all.append(callback)

    def off(
        self,
        event_type: type[Event],
        callback: EventCallback,
    ) -> None:
        """Remove a callback registration."""
        with self._lock:
            regs = self._registrations.get(event_type, [])
            self._registrations[event_type] = [
                r for r in regs if r.callback is not callback
            ]

    def dispatch(self, event: Event) -> None:
        """Dispatch an event to all matching registered callbacks."""
        with self._lock:
            regs = list(self._registrations.get(type(event), []))
            catch_all = list(self._catch_all)

        index = _get_event_index(event)

        for reg in regs:
            if reg.index is not None and reg.index != index:
                continue
            self._executor.submit(self._safe_invoke, reg.callback, event)

        for cb in catch_all:
            self._executor.submit(self._safe_invoke, cb, event)

    def shutdown(self) -> None:
        """Shut down the callback executor."""
        self._executor.shutdown(wait=False)

    @staticmethod
    def _safe_invoke(callback: EventCallback, event: Event) -> None:
        try:
            callback(event)
        except Exception:
            logger.exception("Error in event callback %r", callback)


def _get_event_index(event: Event) -> int | None:
    """Extract the key/knob index from an event, if present."""
    if isinstance(event, (ButtonPress, ButtonRelease)):
        return event.key
    if isinstance(event, (KnobTurn, KnobPress, KnobRelease)):
        return event.knob
    return None
