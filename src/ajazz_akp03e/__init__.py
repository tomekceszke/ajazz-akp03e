"""Python SDK for the Ajazz AKP03E stream deck."""

from importlib.metadata import version

from ajazz_akp03e._device import AKP03E
from ajazz_akp03e._events import (
    ButtonPress,
    ButtonRelease,
    Event,
    KnobPress,
    KnobRelease,
    KnobTurn,
)
from ajazz_akp03e._transport import DeviceInfo
from ajazz_akp03e.errors import (
    AjazzError,
    DeviceConnectionError,
    DeviceNotFoundError,
    ImageError,
    InvalidKeyError,
)

__all__ = [
    "AKP03E",
    "AjazzError",
    "ButtonPress",
    "ButtonRelease",
    "DeviceConnectionError",
    "DeviceInfo",
    "DeviceNotFoundError",
    "Event",
    "ImageError",
    "InvalidKeyError",
    "KnobPress",
    "KnobRelease",
    "KnobTurn",
]

__version__ = version("ajazz-akp03e")
