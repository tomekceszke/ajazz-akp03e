"""Public exception hierarchy for ajazz-akp03e."""

from __future__ import annotations


class AjazzError(Exception):
    """Base exception for all SDK errors."""


class DeviceNotFoundError(AjazzError):
    """No matching AKP03E device was found on the USB bus."""


class DeviceConnectionError(AjazzError):
    """Communication with the device failed."""


class InvalidKeyError(AjazzError):
    """Key or knob index is out of range."""


class ImageError(AjazzError):
    """Image could not be prepared or sent to the device."""
