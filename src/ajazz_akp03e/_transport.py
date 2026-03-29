"""HID transport abstraction for device communication."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Protocol, runtime_checkable

import hid

from ajazz_akp03e._constants import INPUT_SIZE, PACKET_SIZE, PID, USAGE_PAGE, VID
from ajazz_akp03e.errors import DeviceConnectionError, DeviceNotFoundError

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class DeviceInfo:
    """Metadata about a discovered HID device."""

    path: bytes
    vendor_id: int
    product_id: int
    serial_number: str
    product_string: str
    manufacturer_string: str


@runtime_checkable
class HIDTransport(Protocol):
    """Interface for HID device communication.

    Implement this protocol to provide a custom transport (e.g., for testing).
    """

    def open(self) -> None: ...
    def close(self) -> None: ...
    def write(self, data: bytes) -> None: ...
    def read(self, timeout_ms: int = 100) -> bytes | None: ...

    @property
    def is_open(self) -> bool: ...


class AKP03ETransport:
    """Concrete HID transport for the Ajazz AKP03E.

    Discovers the device by VID/PID/usage_page and communicates
    via the ``hid`` package.
    """

    def __init__(self) -> None:
        self._device: hid.Device | None = None
        self._path: bytes | None = None

    @staticmethod
    def enumerate() -> list[DeviceInfo]:
        """List all connected AKP03E devices."""
        results: list[DeviceInfo] = []
        for d in hid.enumerate(VID, PID):
            if d["usage_page"] == USAGE_PAGE:
                results.append(
                    DeviceInfo(
                        path=d["path"],
                        vendor_id=d["vendor_id"],
                        product_id=d["product_id"],
                        serial_number=d.get("serial_number", ""),
                        product_string=d.get("product_string", ""),
                        manufacturer_string=d.get("manufacturer_string", ""),
                    )
                )
        return results

    def _find_path(self) -> bytes:
        """Find the HID path for the first matching device."""
        devices = self.enumerate()
        if not devices:
            raise DeviceNotFoundError(
                "No Ajazz AKP03E found. Is the device plugged in?"
            )
        return devices[0].path

    def open(self) -> None:
        """Open the HID connection to the device."""
        if self._device is not None:
            return
        self._path = self._find_path()
        try:
            self._device = hid.Device(path=self._path)
        except hid.HIDException as exc:
            raise DeviceConnectionError(f"Failed to open device: {exc}") from exc

    def close(self) -> None:
        """Close the HID connection."""
        if self._device is not None:
            import contextlib

            with contextlib.suppress(hid.HIDException):
                self._device.close()
            self._device = None

    def write(self, data: bytes) -> None:
        """Write a packet to the device.

        Args:
            data: Exactly PACKET_SIZE (1025) bytes.

        Raises:
            DeviceConnectionError: If the device is not open or the write fails.
        """
        if self._device is None:
            raise DeviceConnectionError("Device is not open")
        if len(data) != PACKET_SIZE:
            raise DeviceConnectionError(
                f"Packet must be {PACKET_SIZE} bytes, got {len(data)}"
            )
        try:
            self._device.write(data)
        except hid.HIDException as exc:
            raise DeviceConnectionError(f"Write failed: {exc}") from exc

    def read(self, timeout_ms: int = 100) -> bytes | None:
        """Read an input report from the device.

        Returns:
            Raw bytes if data was available, or None on timeout.

        Raises:
            DeviceConnectionError: If the device is not open or the read fails.
        """
        if self._device is None:
            raise DeviceConnectionError("Device is not open")
        try:
            data = self._device.read(INPUT_SIZE, timeout=timeout_ms)
            if data and len(data) > 10:
                return bytes(data)
            return None
        except hid.HIDException as exc:
            raise DeviceConnectionError(f"Read failed: {exc}") from exc

    @property
    def is_open(self) -> bool:
        """Whether the transport currently has an open connection."""
        return self._device is not None
