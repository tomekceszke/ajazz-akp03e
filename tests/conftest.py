"""Shared test fixtures: mock HID transport."""

from __future__ import annotations

from collections.abc import Iterator

import pytest

from ajazz_akp03e._constants import PACKET_SIZE


class MockTransport:
    """In-memory HID transport for testing.

    Records all writes and returns scripted reads.
    """

    def __init__(self) -> None:
        self.written: list[bytes] = []
        self.reads: list[bytes | None] = []
        self._is_open = False
        self._read_index = 0
        self.open_count = 0
        self.close_count = 0

    def open(self) -> None:
        self._is_open = True
        self.open_count += 1

    def close(self) -> None:
        self._is_open = False
        self.close_count += 1

    def write(self, data: bytes) -> None:
        assert len(data) == PACKET_SIZE, (
            f"Expected {PACKET_SIZE} bytes, got {len(data)}"
        )
        self.written.append(data)

    def read(self, timeout_ms: int = 100) -> bytes | None:
        if self._read_index < len(self.reads):
            result = self.reads[self._read_index]
            self._read_index += 1
            return result
        return None

    @property
    def is_open(self) -> bool:
        return self._is_open

    def enqueue_read(self, data: bytes | None) -> None:
        """Add a scripted read response."""
        self.reads.append(data)

    def reset_writes(self) -> None:
        """Clear recorded writes."""
        self.written.clear()


def make_input_report(action: int, state: int = 1) -> bytes:
    """Build a mock 512-byte input report with given action and state."""
    buf = bytearray(512)
    buf[0] = 1  # non-zero = has data
    buf[9] = action
    buf[10] = state
    return bytes(buf)


@pytest.fixture
def transport() -> MockTransport:
    return MockTransport()


@pytest.fixture
def opened_transport(transport: MockTransport) -> Iterator[MockTransport]:
    """A transport that is pre-opened."""
    transport.open()
    yield transport
