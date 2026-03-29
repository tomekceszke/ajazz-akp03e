"""Protocol constants for the Ajazz AKP03E."""

from __future__ import annotations

# USB HID identifiers
VID = 0x0300
PID = 0x3002
USAGE_PAGE = 0xFFA0

# Packet sizes
PACKET_SIZE = 1025  # 1 byte report ID + 1024 bytes data
INPUT_SIZE = 512
DATA_CHUNK_SIZE = 1024

# CRT packet header (bytes 1-5 of every output packet)
HEADER = b"\x43\x52\x54\x00\x00"

# Command payloads (appended after header)
CMD_DIS        = b"\x44\x49\x53\x00\x00"
CMD_LIG        = b"\x4C\x49\x47\x00\x00"
CMD_CLE        = b"\x43\x4C\x45\x00\x00\x00\xFF"
CMD_STP        = b"\x53\x54\x50"
CMD_BAT        = b"\x42\x41\x54\x00\x00"
CMD_SLEEP      = b"\x48\x41\x4E"
CMD_KEEP_ALIVE = b"\x43\x4F\x4E\x4E\x45\x43\x54"
CMD_SHUTDOWN   = b"\x43\x4C\x45\x00\x00\x44\x43"

# Device capabilities
KEY_COUNT = 9
DISPLAY_KEY_COUNT = 6
KNOB_COUNT = 3
DISPLAY_KEY_SIZE = (60, 60)

# Wake cycle delay (seconds)
WAKE_DELAY = 0.5

# Default brightness (0-100). Starts at 0 — displays stay dark until explicitly enabled.
DEFAULT_BRIGHTNESS = 0

# Action code mappings: action_byte -> (event_type, index)
# event_type: "button" or "knob_twist" or "knob_press"
BUTTON_ACTION_CODES: dict[int, int] = {
    0x01: 0,
    0x02: 1,
    0x03: 2,
    0x04: 3,
    0x05: 4,
    0x06: 5,
    0x25: 6,
    0x30: 7,
    0x31: 8,
}

KNOB_TWIST_CODES: dict[int, tuple[int, int]] = {
    0x90: (0, -1),  # dial 0, CCW
    0x91: (0, 1),   # dial 0, CW
    0x50: (1, -1),  # dial 1, CCW
    0x51: (1, 1),   # dial 1, CW
    0x60: (2, -1),  # dial 2, CCW
    0x61: (2, 1),   # dial 2, CW
}

KNOB_PRESS_CODES: dict[int, int] = {
    0x33: 0,
    0x35: 1,
    0x34: 2,
}
