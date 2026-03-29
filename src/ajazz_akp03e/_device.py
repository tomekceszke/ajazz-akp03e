"""High-level device interface for the Ajazz AKP03E."""

from __future__ import annotations

import logging
import threading
import time
from collections.abc import Callable
from typing import Any

from ajazz_akp03e._constants import (
    DATA_CHUNK_SIZE,
    DEFAULT_BRIGHTNESS,
    DISPLAY_KEY_COUNT,
    DISPLAY_KEY_SIZE,
    KEY_COUNT,
    KNOB_COUNT,
    WAKE_DELAY,
)
from ajazz_akp03e._events import (
    ButtonPress,
    ButtonRelease,
    Event,
    EventDispatcher,
    KnobPress,
    KnobRelease,
    KnobTurn,
)
from ajazz_akp03e._image import prepare_key_image
from ajazz_akp03e._protocol import (
    build_brightness_packet,
    build_clear_packet,
    build_flush_packet,
    build_image_announce_packet,
    build_image_chunk,
    build_init_packet,
    build_keep_alive_packet,
    build_shutdown_packet,
    build_sleep_packet,
    parse_input,
)
from ajazz_akp03e._transport import AKP03ETransport, HIDTransport
from ajazz_akp03e.errors import DeviceConnectionError, InvalidKeyError

logger = logging.getLogger(__name__)


class AKP03E:
    """High-level interface to the Ajazz AKP03E stream deck.

    Supports context manager usage::

        with AKP03E() as deck:
            deck.on_button_press(0, my_handler)
            deck.start()
            deck.wait()

    Args:
        transport: Custom HID transport (for testing). If None, uses
            the default ``AKP03ETransport``.
        brightness: Initial display brightness (0-100).
        auto_reconnect: Whether to automatically reconnect on errors.
        reconnect_delay: Seconds to wait before reconnection attempts.
    """

    KEY_COUNT: int = KEY_COUNT
    DISPLAY_KEY_COUNT: int = DISPLAY_KEY_COUNT
    KNOB_COUNT: int = KNOB_COUNT

    def __init__(
        self,
        *,
        transport: HIDTransport | None = None,
        brightness: int = DEFAULT_BRIGHTNESS,
        auto_reconnect: bool = True,
        reconnect_delay: float = 2.0,
    ) -> None:
        self._transport = transport or AKP03ETransport()
        self._brightness = brightness
        self._auto_reconnect = auto_reconnect
        self._reconnect_delay = reconnect_delay

        self._dispatcher = EventDispatcher()
        self._write_lock = threading.Lock()
        self._reader_thread: threading.Thread | None = None
        self._stop_event = threading.Event()

    # -- Context manager --

    def __enter__(self) -> AKP03E:
        self.open()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: Any,
    ) -> None:
        self.close()

    # -- Connection lifecycle --

    def open(self) -> None:
        """Open the device connection and perform the wake cycle.

        The AKP03E requires a specific wake sequence: connect, send init
        commands, close, wait briefly, then reconnect.
        """
        # Phase 1: Wake
        self._transport.open()
        self._send_init_sequence()
        self._transport.close()
        time.sleep(WAKE_DELAY)

        # Phase 2: Reconnect for operation
        self._transport.open()
        self._send_init_sequence()

    def close(self) -> None:
        """Stop the event loop and close the device connection."""
        self.stop()
        self._dispatcher.shutdown()
        self._transport.close()

    @property
    def connected(self) -> bool:
        """Whether the device is currently connected."""
        return self._transport.is_open

    # -- Device control --

    def set_brightness(self, percent: int) -> None:
        """Set display brightness.

        Args:
            percent: Brightness level (0-100).

        Raises:
            ValueError: If percent is outside 0-100.
        """
        packet = build_brightness_packet(percent)
        self._write(packet)
        self._brightness = percent

    def set_key_image(
        self,
        key: int,
        image: Any,  # PIL Image, str, Path, or bytes
        brightness: int | None = None,
    ) -> None:
        """Set the image on a display key.

        Args:
            key: Button index (0-5 for display keys).
            image: PIL Image, file path (str/Path), or raw JPEG bytes.
            brightness: Optional brightness to set after the image (0-100).
                If None, brightness is left unchanged.

        Raises:
            InvalidKeyError: If key is not a display key (0-5).
            ImageError: If the image cannot be processed.
        """
        if not 0 <= key < DISPLAY_KEY_COUNT:
            raise InvalidKeyError(
                f"Display key must be 0-{DISPLAY_KEY_COUNT - 1}, got {key}"
            )

        jpeg_data = prepare_key_image(image)
        self._send_image(key, jpeg_data)

        if brightness is not None:
            self.set_brightness(brightness)

    def clear_key_image(self, key: int) -> None:
        """Clear the image on a single display key.

        This sends a minimal 1x1 black JPEG to the key.

        Args:
            key: Button index (0-5 for display keys).

        Raises:
            InvalidKeyError: If key is not a display key (0-5).
        """
        if not 0 <= key < DISPLAY_KEY_COUNT:
            raise InvalidKeyError(
                f"Display key must be 0-{DISPLAY_KEY_COUNT - 1}, got {key}"
            )
        from PIL import Image as _Image

        black = prepare_key_image(_Image.new("RGB", DISPLAY_KEY_SIZE, (0, 0, 0)))
        self._send_image(key, black)

    def clear_all_images(self) -> None:
        """Clear all button display images."""
        self._write(build_clear_packet())
        self._write(build_flush_packet())

    def sleep(self) -> None:
        """Put the device into low-power standby. Displays turn off.

        Call ``wake()`` to resume normal operation.
        """
        self._write(build_shutdown_packet())
        self._write(build_sleep_packet())

    def wake(self) -> None:
        """Wake the device from standby and restore displays."""
        self._send_init_sequence()

    def keep_alive(self) -> None:
        """Send a heartbeat to prevent the device from auto-sleeping."""
        self._write(build_keep_alive_packet())

    # -- Event registration --

    def on_button_press(
        self, key: int, callback: Callable[[ButtonPress], None]
    ) -> None:
        """Register a callback for when a button is pressed.

        Args:
            key: Button index (0-8).
            callback: Function called with a ``ButtonPress`` event.
        """
        self._validate_key(key)
        self._dispatcher.on(ButtonPress, callback, index=key)

    def on_button_release(
        self, key: int, callback: Callable[[ButtonRelease], None]
    ) -> None:
        """Register a callback for when a button is released.

        Args:
            key: Button index (0-8).
            callback: Function called with a ``ButtonRelease`` event.
        """
        self._validate_key(key)
        self._dispatcher.on(ButtonRelease, callback, index=key)

    def on_knob_turn(
        self, knob: int, callback: Callable[[KnobTurn], None]
    ) -> None:
        """Register a callback for when a knob is turned.

        Args:
            knob: Knob index (0-2).
            callback: Function called with a ``KnobTurn`` event.
        """
        self._validate_knob(knob)
        self._dispatcher.on(KnobTurn, callback, index=knob)

    def on_knob_press(
        self, knob: int, callback: Callable[[KnobPress], None]
    ) -> None:
        """Register a callback for when a knob is pressed.

        Args:
            knob: Knob index (0-2).
            callback: Function called with a ``KnobPress`` event.
        """
        self._validate_knob(knob)
        self._dispatcher.on(KnobPress, callback, index=knob)

    def on_knob_release(
        self, knob: int, callback: Callable[[KnobRelease], None]
    ) -> None:
        """Register a callback for when a knob is released.

        Args:
            knob: Knob index (0-2).
            callback: Function called with a ``KnobRelease`` event.
        """
        self._validate_knob(knob)
        self._dispatcher.on(KnobRelease, callback, index=knob)

    def on_event(self, callback: Callable[[Event], None]) -> None:
        """Register a catch-all callback for every event.

        Args:
            callback: Function called with any ``Event`` subclass.
        """
        self._dispatcher.on_any(callback)

    # -- Event loop --

    def start(self) -> None:
        """Start the background event reader thread.

        The reader thread continuously polls the device for input events
        and dispatches them to registered callbacks.
        """
        if self._reader_thread is not None and self._reader_thread.is_alive():
            return

        self._stop_event.clear()
        self._reader_thread = threading.Thread(
            target=self._read_loop,
            name="akp03e-reader",
            daemon=True,
        )
        self._reader_thread.start()

    def stop(self) -> None:
        """Signal the reader thread to stop."""
        self._stop_event.set()
        if self._reader_thread is not None:
            self._reader_thread.join(timeout=2.0)
            self._reader_thread = None

    def wait(self) -> None:
        """Block the calling thread until ``stop()`` is called.

        Typically called from the main thread to keep the program alive
        while the event loop runs. Responds to KeyboardInterrupt.
        """
        try:
            while not self._stop_event.is_set():
                self._stop_event.wait(timeout=0.5)
        except KeyboardInterrupt:
            self.stop()

    # -- Internal methods --

    def _send_init_sequence(self) -> None:
        """Send the DIS/LIG/CLE/STP initialization sequence."""
        self._write(build_init_packet())
        self._write(build_brightness_packet(self._brightness))
        self._write(build_clear_packet())
        self._write(build_flush_packet())

    def _send_image(self, key: int, jpeg_data: bytes) -> None:
        """Send JPEG data to a display key via BAT + chunks + STP."""
        with self._write_lock:
            self._transport.write(build_image_announce_packet(key, len(jpeg_data)))

            offset = 0
            while offset < len(jpeg_data):
                chunk = jpeg_data[offset : offset + DATA_CHUNK_SIZE]
                self._transport.write(build_image_chunk(chunk))
                offset += DATA_CHUNK_SIZE

            self._transport.write(build_flush_packet())

    def _write(self, data: bytes) -> None:
        """Thread-safe write to the transport."""
        with self._write_lock:
            self._transport.write(data)

    def _read_loop(self) -> None:
        """Background reader loop: read input, parse, dispatch events."""
        while not self._stop_event.is_set():
            try:
                data = self._transport.read(timeout_ms=100)
                if data is not None:
                    event = parse_input(data, device=self)
                    if event is not None:
                        self._dispatcher.dispatch(event)
            except DeviceConnectionError:
                if not self._auto_reconnect or self._stop_event.is_set():
                    break
                logger.warning("Connection lost, attempting reconnect...")
                self._reconnect()
            except Exception:
                logger.exception("Unexpected error in reader loop")
                if not self._auto_reconnect or self._stop_event.is_set():
                    break
                self._reconnect()

    def _reconnect(self) -> None:
        """Attempt to reconnect to the device."""
        self._transport.close()
        self._stop_event.wait(timeout=self._reconnect_delay)
        if self._stop_event.is_set():
            return
        try:
            self._transport.open()
            self._send_init_sequence()
            logger.info("Reconnected successfully")
        except Exception:
            logger.warning("Reconnection failed, will retry...")

    def _validate_key(self, key: int) -> None:
        if not 0 <= key < KEY_COUNT:
            raise InvalidKeyError(f"Key must be 0-{KEY_COUNT - 1}, got {key}")

    def _validate_knob(self, knob: int) -> None:
        if not 0 <= knob < KNOB_COUNT:
            raise InvalidKeyError(f"Knob must be 0-{KNOB_COUNT - 1}, got {knob}")
