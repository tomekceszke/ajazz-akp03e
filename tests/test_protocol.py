"""Tests for protocol packet building and input parsing."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from ajazz_akp03e._constants import HEADER, PACKET_SIZE
from ajazz_akp03e._events import (
    ButtonPress,
    ButtonRelease,
    KnobPress,
    KnobRelease,
    KnobTurn,
)
from ajazz_akp03e._protocol import (
    build_brightness_packet,
    build_clear_packet,
    build_flush_packet,
    build_image_announce_packet,
    build_image_chunk,
    build_init_packet,
    build_keep_alive_packet,
    build_packet,
    build_shutdown_packet,
    build_sleep_packet,
    parse_input,
)

from .conftest import make_input_report


class TestBuildPacket:
    def test_packet_size(self) -> None:
        pkt = build_packet(b"\x01\x02")
        assert len(pkt) == PACKET_SIZE

    def test_report_id_zero(self) -> None:
        pkt = build_packet(b"\x01")
        assert pkt[0] == 0

    def test_crt_header(self) -> None:
        pkt = build_packet(b"\x01")
        assert pkt[1:6] == HEADER

    def test_command_payload(self) -> None:
        pkt = build_packet(b"\xAA\xBB\xCC")
        assert pkt[6] == 0xAA
        assert pkt[7] == 0xBB
        assert pkt[8] == 0xCC

    def test_remaining_bytes_zero(self) -> None:
        pkt = build_packet(b"\x01")
        assert all(b == 0 for b in pkt[7:])


class TestBuildInitPacket:
    def test_dis_command(self) -> None:
        pkt = build_init_packet()
        assert pkt[6:11] == b"\x44\x49\x53\x00\x00"


class TestBuildBrightnessPacket:
    def test_brightness_50(self) -> None:
        pkt = build_brightness_packet(50)
        assert pkt[6:11] == b"\x4C\x49\x47\x00\x00"
        assert pkt[11] == 50

    def test_brightness_0(self) -> None:
        pkt = build_brightness_packet(0)
        assert pkt[11] == 0

    def test_brightness_100(self) -> None:
        pkt = build_brightness_packet(100)
        assert pkt[11] == 100

    def test_brightness_negative_raises(self) -> None:
        with pytest.raises(ValueError, match="0-100"):
            build_brightness_packet(-1)

    def test_brightness_over_100_raises(self) -> None:
        with pytest.raises(ValueError, match="0-100"):
            build_brightness_packet(101)


class TestBuildClearPacket:
    def test_cle_command(self) -> None:
        pkt = build_clear_packet()
        assert pkt[6:13] == b"\x43\x4C\x45\x00\x00\x00\xFF"


class TestBuildFlushPacket:
    def test_stp_command(self) -> None:
        pkt = build_flush_packet()
        assert pkt[6:9] == b"\x53\x54\x50"


class TestBuildSleepPacket:
    def test_han_command(self) -> None:
        pkt = build_sleep_packet()
        assert pkt[6:9] == b"\x48\x41\x4E"


class TestBuildKeepAlivePacket:
    def test_connect_command(self) -> None:
        pkt = build_keep_alive_packet()
        assert pkt[6:13] == b"\x43\x4F\x4E\x4E\x45\x43\x54"


class TestBuildShutdownPacket:
    def test_shutdown_command(self) -> None:
        pkt = build_shutdown_packet()
        assert pkt[6:13] == b"\x43\x4C\x45\x00\x00\x44\x43"


class TestBuildImageAnnouncePacket:
    def test_bat_header(self) -> None:
        pkt = build_image_announce_packet(0, 1000)
        assert pkt[6:11] == b"\x42\x41\x54\x00\x00"

    def test_size_encoding(self) -> None:
        pkt = build_image_announce_packet(0, 0x1234)
        assert pkt[11] == 0x12  # size_hi
        assert pkt[12] == 0x34  # size_lo

    def test_key_plus_one(self) -> None:
        """Protocol uses 1-based key indexing."""
        pkt = build_image_announce_packet(0, 100)
        assert pkt[13] == 1
        pkt = build_image_announce_packet(5, 100)
        assert pkt[13] == 6


class TestBuildImageChunk:
    def test_chunk_size(self) -> None:
        chunk = build_image_chunk(b"\xAA" * 100)
        assert len(chunk) == PACKET_SIZE

    def test_chunk_data_placement(self) -> None:
        data = b"\xAA\xBB\xCC"
        chunk = build_image_chunk(data)
        assert chunk[1:4] == data

    def test_chunk_report_id_zero(self) -> None:
        chunk = build_image_chunk(b"\x01")
        assert chunk[0] == 0


class TestParseInput:
    @pytest.fixture
    def device(self) -> MagicMock:
        return MagicMock()

    def test_empty_report_returns_none(self, device: MagicMock) -> None:
        data = bytes(512)  # all zeros
        assert parse_input(data, device) is None

    def test_short_data_returns_none(self, device: MagicMock) -> None:
        assert parse_input(b"\x01" * 5, device) is None

    # Display buttons 0-5
    @pytest.mark.parametrize("action,key", [
        (0x01, 0), (0x02, 1), (0x03, 2), (0x04, 3), (0x05, 4), (0x06, 5),
    ])
    def test_display_button_press(
        self, device: MagicMock, action: int, key: int,
    ) -> None:
        data = make_input_report(action, state=1)
        event = parse_input(data, device)
        assert isinstance(event, ButtonPress)
        assert event.key == key
        assert event.device is device

    @pytest.mark.parametrize("action,key", [
        (0x01, 0), (0x02, 1), (0x03, 2), (0x04, 3), (0x05, 4), (0x06, 5),
    ])
    def test_display_button_release(
        self, device: MagicMock, action: int, key: int,
    ) -> None:
        data = make_input_report(action, state=0)
        event = parse_input(data, device)
        assert isinstance(event, ButtonRelease)
        assert event.key == key

    # Side buttons 6-8
    @pytest.mark.parametrize("action,key", [
        (0x25, 6), (0x30, 7), (0x31, 8),
    ])
    def test_side_button_press(self, device: MagicMock, action: int, key: int) -> None:
        data = make_input_report(action, state=1)
        event = parse_input(data, device)
        assert isinstance(event, ButtonPress)
        assert event.key == key

    @pytest.mark.parametrize("action,key", [
        (0x25, 6), (0x30, 7), (0x31, 8),
    ])
    def test_side_button_release(
        self, device: MagicMock, action: int, key: int,
    ) -> None:
        data = make_input_report(action, state=0)
        event = parse_input(data, device)
        assert isinstance(event, ButtonRelease)
        assert event.key == key

    # Encoder twist
    @pytest.mark.parametrize("action,knob,direction", [
        (0x90, 0, -1), (0x91, 0, 1),
        (0x50, 1, -1), (0x51, 1, 1),
        (0x60, 2, -1), (0x61, 2, 1),
    ])
    def test_knob_twist(
        self, device: MagicMock, action: int, knob: int, direction: int,
    ) -> None:
        data = make_input_report(action)
        event = parse_input(data, device)
        assert isinstance(event, KnobTurn)
        assert event.knob == knob
        assert event.direction == direction

    # Encoder press
    @pytest.mark.parametrize("action,knob", [
        (0x33, 0), (0x35, 1), (0x34, 2),
    ])
    def test_knob_press(self, device: MagicMock, action: int, knob: int) -> None:
        data = make_input_report(action, state=1)
        event = parse_input(data, device)
        assert isinstance(event, KnobPress)
        assert event.knob == knob

    @pytest.mark.parametrize("action,knob", [
        (0x33, 0), (0x35, 1), (0x34, 2),
    ])
    def test_knob_release(self, device: MagicMock, action: int, knob: int) -> None:
        data = make_input_report(action, state=0)
        event = parse_input(data, device)
        assert isinstance(event, KnobRelease)
        assert event.knob == knob

    def test_unknown_action_returns_none(self, device: MagicMock) -> None:
        data = make_input_report(0xFF)
        assert parse_input(data, device) is None
