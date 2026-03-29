"""Pure protocol functions for packet building and input parsing.

All functions in this module are pure — no I/O, no side effects.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from ajazz_akp03e._constants import (
    BUTTON_ACTION_CODES,
    CMD_BAT,
    CMD_CLE,
    CMD_DIS,
    CMD_KEEP_ALIVE,
    CMD_LIG,
    CMD_SHUTDOWN,
    CMD_SLEEP,
    CMD_STP,
    HEADER,
    KNOB_PRESS_CODES,
    KNOB_TWIST_CODES,
    PACKET_SIZE,
)
from ajazz_akp03e._events import (
    ButtonPress,
    ButtonRelease,
    Event,
    KnobPress,
    KnobRelease,
    KnobTurn,
)

if TYPE_CHECKING:
    from ajazz_akp03e._device import AKP03E


def build_packet(cmd: bytes) -> bytes:
    """Build a 1025-byte output packet with CRT header."""
    buf = bytearray(PACKET_SIZE)
    buf[1:6] = HEADER
    buf[6 : 6 + len(cmd)] = cmd
    return bytes(buf)


def build_init_packet() -> bytes:
    """Build the DIS initialization packet."""
    return build_packet(CMD_DIS)


def build_brightness_packet(percent: int) -> bytes:
    """Build a LIG brightness packet.

    Args:
        percent: Brightness level 0-100.

    Raises:
        ValueError: If percent is outside 0-100 range.
    """
    if not 0 <= percent <= 100:
        raise ValueError(f"Brightness must be 0-100, got {percent}")
    return build_packet(CMD_LIG + bytes([percent]))


def build_clear_packet() -> bytes:
    """Build the CLE clear-all-images packet."""
    return build_packet(CMD_CLE)


def build_flush_packet() -> bytes:
    """Build the STP flush packet."""
    return build_packet(CMD_STP)


def build_image_announce_packet(key: int, image_size: int) -> bytes:
    """Build the BAT image upload announcement packet.

    Args:
        key: Button index (0-based).
        image_size: Size of the JPEG data in bytes.
    """
    size_hi = (image_size >> 8) & 0xFF
    size_lo = image_size & 0xFF
    return build_packet(CMD_BAT + bytes([size_hi, size_lo, key + 1]))


def build_image_chunk(data: bytes) -> bytes:
    """Build a raw data chunk packet for image streaming.

    Args:
        data: Up to 1024 bytes of image data.
    """
    buf = bytearray(PACKET_SIZE)
    buf[1 : 1 + len(data)] = data
    return bytes(buf)


def build_sleep_packet() -> bytes:
    """Build the sleep/standby packet."""
    return build_packet(CMD_SLEEP)


def build_keep_alive_packet() -> bytes:
    """Build the keep-alive heartbeat packet."""
    return build_packet(CMD_KEEP_ALIVE)


def build_shutdown_packet() -> bytes:
    """Build the shutdown packet (send before sleep for a clean power-down)."""
    return build_packet(CMD_SHUTDOWN)


def parse_input(data: bytes, device: AKP03E) -> Event | None:
    """Parse a 512-byte input report into a typed Event.

    Args:
        data: Raw input bytes from the device.
        device: The AKP03E instance (attached to the event).

    Returns:
        An Event subclass, or None if the report is empty.
    """
    if len(data) < 11 or data[0] == 0:
        return None

    action = data[9]
    state = data[10]

    # Display buttons (0x01-0x06) and side buttons (0x25, 0x30, 0x31)
    if action in BUTTON_ACTION_CODES:
        key = BUTTON_ACTION_CODES[action]
        if state:
            return ButtonPress(device=device, key=key)
        return ButtonRelease(device=device, key=key)

    # Encoder twist
    if action in KNOB_TWIST_CODES:
        knob, direction = KNOB_TWIST_CODES[action]
        return KnobTurn(device=device, knob=knob, direction=direction)

    # Encoder press
    if action in KNOB_PRESS_CODES:
        knob = KNOB_PRESS_CODES[action]
        if state:
            return KnobPress(device=device, knob=knob)
        return KnobRelease(device=device, knob=knob)

    return None
