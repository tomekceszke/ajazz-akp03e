"""Tests for the AKP03E device class."""

from __future__ import annotations

import time

import pytest

from ajazz_akp03e._device import AKP03E
from ajazz_akp03e._events import ButtonPress, KnobTurn
from ajazz_akp03e.errors import InvalidKeyError

from .conftest import MockTransport, make_input_report


class TestAKP03EInit:
    def test_open_performs_wake_cycle(self, transport: MockTransport) -> None:
        """open() should: connect, init, close, reconnect, init."""
        deck = AKP03E(transport=transport, brightness=50)
        deck.open()

        # Wake: open, init (4 pkts), close, open, init (4 pkts)
        assert transport.open_count == 2
        assert transport.close_count == 1
        # 4 init packets (DIS, LIG, CLE, STP) x 2 phases = 8
        assert len(transport.written) == 8

        deck.close()

    def test_init_sequence_commands(self, transport: MockTransport) -> None:
        """Verify the DIS/LIG/CLE/STP init sequence."""
        deck = AKP03E(transport=transport, brightness=50)
        deck.open()

        # Check first 4 packets (phase 1 init)
        dis = transport.written[0]
        assert dis[6:11] == b"\x44\x49\x53\x00\x00"

        lig = transport.written[1]
        assert lig[6:11] == b"\x4C\x49\x47\x00\x00"
        assert lig[11] == 50

        cle = transport.written[2]
        assert cle[6:13] == b"\x43\x4C\x45\x00\x00\x00\xFF"

        stp = transport.written[3]
        assert stp[6:9] == b"\x53\x54\x50"

        deck.close()

    def test_default_brightness_is_zero(self, transport: MockTransport) -> None:
        deck = AKP03E(transport=transport)
        deck.open()

        lig = transport.written[1]
        assert lig[11] == 0

        deck.close()

    def test_custom_brightness(self, transport: MockTransport) -> None:
        deck = AKP03E(transport=transport, brightness=80)
        deck.open()

        lig = transport.written[1]
        assert lig[11] == 80

        deck.close()


class TestContextManager:
    def test_context_manager(self, transport: MockTransport) -> None:
        with AKP03E(transport=transport):
            assert transport.is_open

        assert not transport.is_open

    def test_connected_property(self, transport: MockTransport) -> None:
        deck = AKP03E(transport=transport)
        assert not deck.connected
        deck.open()
        assert deck.connected
        deck.close()
        assert not deck.connected


class TestBrightness:
    def test_set_brightness(self, transport: MockTransport) -> None:
        deck = AKP03E(transport=transport)
        deck.open()
        transport.reset_writes()

        deck.set_brightness(75)

        assert len(transport.written) == 1
        assert transport.written[0][11] == 75

        deck.close()

    def test_brightness_validation(self, transport: MockTransport) -> None:
        deck = AKP03E(transport=transport)
        deck.open()

        with pytest.raises(ValueError):
            deck.set_brightness(-1)
        with pytest.raises(ValueError):
            deck.set_brightness(101)

        deck.close()


class TestKeyImage:
    def test_set_key_image_raw_bytes(self, transport: MockTransport) -> None:
        deck = AKP03E(transport=transport)
        deck.open()
        transport.reset_writes()

        jpeg_data = b"\xFF\xD8" + b"\x00" * 500 + b"\xFF\xD9"

        deck.set_key_image(0, jpeg_data)

        # Should have: BAT announce + 1 data chunk + STP flush
        assert len(transport.written) == 3

        # BAT announce
        bat = transport.written[0]
        assert bat[6:11] == b"\x42\x41\x54\x00\x00"
        assert bat[13] == 1  # key 0 -> protocol key 1

        # STP flush
        stp = transport.written[-1]
        assert stp[6:9] == b"\x53\x54\x50"

        deck.close()

    def test_set_key_image_invalid_key(self, transport: MockTransport) -> None:
        deck = AKP03E(transport=transport)
        deck.open()

        with pytest.raises(InvalidKeyError):
            deck.set_key_image(6, b"\xFF\xD8\xFF\xD9")
        with pytest.raises(InvalidKeyError):
            deck.set_key_image(-1, b"\xFF\xD8\xFF\xD9")

        deck.close()

    def test_clear_all_images(self, transport: MockTransport) -> None:
        deck = AKP03E(transport=transport)
        deck.open()
        transport.reset_writes()

        deck.clear_all_images()

        assert len(transport.written) == 2  # CLE + STP
        assert transport.written[0][6:13] == b"\x43\x4C\x45\x00\x00\x00\xFF"
        assert transport.written[1][6:9] == b"\x53\x54\x50"

        deck.close()

    def test_set_key_image_with_brightness(self, transport: MockTransport) -> None:
        deck = AKP03E(transport=transport)
        deck.open()
        transport.reset_writes()

        jpeg_data = b"\xFF\xD8" + b"\x00" * 500 + b"\xFF\xD9"
        deck.set_key_image(0, jpeg_data, brightness=75)

        # BAT + chunk + STP + LIG (brightness)
        assert len(transport.written) == 4
        lig = transport.written[-1]
        assert lig[6:11] == b"\x4C\x49\x47\x00\x00"
        assert lig[11] == 75

        deck.close()

    def test_set_key_image_no_brightness_unchanged(
        self, transport: MockTransport
    ) -> None:
        deck = AKP03E(transport=transport)
        deck.open()
        transport.reset_writes()

        jpeg_data = b"\xFF\xD8" + b"\x00" * 500 + b"\xFF\xD9"
        deck.set_key_image(0, jpeg_data)

        # Only BAT + chunk + STP — no brightness packet
        assert len(transport.written) == 3

        deck.close()


class TestDisplayPower:
    def test_sleep_sends_shutdown_then_sleep(
        self, transport: MockTransport
    ) -> None:
        deck = AKP03E(transport=transport)
        deck.open()
        transport.reset_writes()

        deck.sleep()

        assert len(transport.written) == 2
        assert transport.written[0][6:13] == b"\x43\x4C\x45\x00\x00\x44\x43"
        assert transport.written[1][6:9] == b"\x48\x41\x4E"

        deck.close()

    def test_wake_sends_init_sequence(self, transport: MockTransport) -> None:
        deck = AKP03E(transport=transport)
        deck.open()
        transport.reset_writes()

        deck.wake()

        assert len(transport.written) == 4
        assert transport.written[0][6:11] == b"\x44\x49\x53\x00\x00"  # DIS
        assert transport.written[3][6:9] == b"\x53\x54\x50"           # STP

        deck.close()

    def test_keep_alive_sends_heartbeat(self, transport: MockTransport) -> None:
        deck = AKP03E(transport=transport)
        deck.open()
        transport.reset_writes()

        deck.keep_alive()

        assert len(transport.written) == 1
        assert transport.written[0][6:13] == b"\x43\x4F\x4E\x4E\x45\x43\x54"

        deck.close()


class TestEventRegistration:
    def test_valid_key_registration(self, transport: MockTransport) -> None:
        deck = AKP03E(transport=transport)
        deck.on_button_press(0, lambda e: None)
        deck.on_button_press(8, lambda e: None)

    def test_invalid_key_raises(self, transport: MockTransport) -> None:
        deck = AKP03E(transport=transport)
        with pytest.raises(InvalidKeyError):
            deck.on_button_press(9, lambda e: None)
        with pytest.raises(InvalidKeyError):
            deck.on_button_press(-1, lambda e: None)

    def test_valid_knob_registration(self, transport: MockTransport) -> None:
        deck = AKP03E(transport=transport)
        deck.on_knob_turn(0, lambda e: None)
        deck.on_knob_turn(2, lambda e: None)

    def test_invalid_knob_raises(self, transport: MockTransport) -> None:
        deck = AKP03E(transport=transport)
        with pytest.raises(InvalidKeyError):
            deck.on_knob_turn(3, lambda e: None)


class TestEventLoop:
    def test_start_stop(self, transport: MockTransport) -> None:
        deck = AKP03E(transport=transport)
        deck.open()

        deck.start()
        time.sleep(0.1)
        deck.stop()

        deck.close()

    def test_button_event_fires_callback(self, transport: MockTransport) -> None:
        # Enqueue a button press read
        transport.enqueue_read(make_input_report(0x01, state=1))

        deck = AKP03E(transport=transport)
        deck.open()

        results: list[ButtonPress] = []
        deck.on_button_press(0, results.append)

        deck.start()
        time.sleep(0.3)
        deck.stop()
        deck.close()

        assert len(results) == 1
        assert results[0].key == 0
        assert results[0].device is deck

    def test_knob_event_fires_callback(self, transport: MockTransport) -> None:
        transport.enqueue_read(make_input_report(0x91, state=0))

        deck = AKP03E(transport=transport)
        deck.open()

        results: list[KnobTurn] = []
        deck.on_knob_turn(0, results.append)

        deck.start()
        time.sleep(0.3)
        deck.stop()
        deck.close()

        assert len(results) == 1
        assert results[0].knob == 0
        assert results[0].direction == 1

    def test_catch_all_receives_events(self, transport: MockTransport) -> None:
        transport.enqueue_read(make_input_report(0x01, state=1))
        transport.enqueue_read(make_input_report(0x91, state=0))

        deck = AKP03E(transport=transport)
        deck.open()

        results: list[object] = []
        deck.on_event(results.append)

        deck.start()
        time.sleep(0.3)
        deck.stop()
        deck.close()

        assert len(results) == 2

    def test_double_start_is_safe(self, transport: MockTransport) -> None:
        deck = AKP03E(transport=transport)
        deck.open()

        deck.start()
        deck.start()  # should not raise or create duplicate threads
        time.sleep(0.1)
        deck.stop()
        deck.close()
