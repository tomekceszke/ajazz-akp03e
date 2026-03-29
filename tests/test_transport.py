"""Tests for the transport layer (using mocks — no hardware needed)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from ajazz_akp03e._constants import PACKET_SIZE, USAGE_PAGE
from ajazz_akp03e._transport import AKP03ETransport, DeviceInfo
from ajazz_akp03e.errors import DeviceConnectionError, DeviceNotFoundError


class TestDeviceInfo:
    def test_frozen(self) -> None:
        info = DeviceInfo(
            path=b"/dev/hid0",
            vendor_id=0x0300,
            product_id=0x3002,
            serial_number="",
            product_string="AKP03E",
            manufacturer_string="Ajazz",
        )
        with pytest.raises(AttributeError):
            info.path = b"/other"  # type: ignore[misc]


class TestAKP03ETransportEnumerate:
    @patch("ajazz_akp03e._transport.hid")
    def test_filters_by_usage_page(self, mock_hid: MagicMock) -> None:
        mock_hid.enumerate.return_value = [
            {
                "path": b"/dev/hid0",
                "vendor_id": 0x0300,
                "product_id": 0x3002,
                "usage_page": USAGE_PAGE,
                "serial_number": "",
                "product_string": "AKP03E",
                "manufacturer_string": "Ajazz",
            },
            {
                "path": b"/dev/hid1",
                "vendor_id": 0x0300,
                "product_id": 0x3002,
                "usage_page": 0x0001,  # wrong usage page (keyboard)
                "serial_number": "",
                "product_string": "AKP03E",
                "manufacturer_string": "Ajazz",
            },
        ]

        devices = AKP03ETransport.enumerate()
        assert len(devices) == 1
        assert devices[0].path == b"/dev/hid0"

    @patch("ajazz_akp03e._transport.hid")
    def test_no_devices(self, mock_hid: MagicMock) -> None:
        mock_hid.enumerate.return_value = []
        devices = AKP03ETransport.enumerate()
        assert devices == []


class TestAKP03ETransportOpenClose:
    @patch("ajazz_akp03e._transport.hid")
    def test_open_no_device_raises(self, mock_hid: MagicMock) -> None:
        mock_hid.enumerate.return_value = []
        transport = AKP03ETransport()

        with pytest.raises(DeviceNotFoundError):
            transport.open()

    @patch("ajazz_akp03e._transport.hid")
    def test_open_hid_failure_raises(self, mock_hid: MagicMock) -> None:
        import hid as real_hid

        mock_hid.enumerate.return_value = [
            {
                "path": b"/dev/hid0",
                "vendor_id": 0x0300,
                "product_id": 0x3002,
                "usage_page": USAGE_PAGE,
                "serial_number": "",
                "product_string": "AKP03E",
                "manufacturer_string": "Ajazz",
            },
        ]
        mock_hid.HIDException = real_hid.HIDException
        mock_hid.Device.side_effect = real_hid.HIDException("access denied")

        transport = AKP03ETransport()
        with pytest.raises(DeviceConnectionError):
            transport.open()

    @patch("ajazz_akp03e._transport.hid")
    def test_is_open_lifecycle(self, mock_hid: MagicMock) -> None:
        mock_hid.enumerate.return_value = [
            {
                "path": b"/dev/hid0",
                "vendor_id": 0x0300,
                "product_id": 0x3002,
                "usage_page": USAGE_PAGE,
                "serial_number": "",
                "product_string": "",
                "manufacturer_string": "",
            },
        ]
        mock_device = MagicMock()
        mock_hid.Device.return_value = mock_device

        transport = AKP03ETransport()
        assert not transport.is_open

        transport.open()
        assert transport.is_open

        transport.close()
        assert not transport.is_open


class TestAKP03ETransportWriteRead:
    @patch("ajazz_akp03e._transport.hid")
    def test_write_when_closed_raises(self, mock_hid: MagicMock) -> None:
        transport = AKP03ETransport()
        with pytest.raises(DeviceConnectionError, match="not open"):
            transport.write(bytes(PACKET_SIZE))

    @patch("ajazz_akp03e._transport.hid")
    def test_write_wrong_size_raises(self, mock_hid: MagicMock) -> None:
        mock_hid.enumerate.return_value = [
            {
                "path": b"/dev/hid0",
                "vendor_id": 0x0300,
                "product_id": 0x3002,
                "usage_page": USAGE_PAGE,
                "serial_number": "",
                "product_string": "",
                "manufacturer_string": "",
            },
        ]
        mock_hid.Device.return_value = MagicMock()

        transport = AKP03ETransport()
        transport.open()

        with pytest.raises(DeviceConnectionError, match="1025"):
            transport.write(b"\x00" * 100)

    @patch("ajazz_akp03e._transport.hid")
    def test_read_when_closed_raises(self, mock_hid: MagicMock) -> None:
        transport = AKP03ETransport()
        with pytest.raises(DeviceConnectionError, match="not open"):
            transport.read()
