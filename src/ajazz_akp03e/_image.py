"""Image preparation for button display keys."""

from __future__ import annotations

import io
from pathlib import Path

from PIL import Image

from ajazz_akp03e._constants import DISPLAY_KEY_SIZE
from ajazz_akp03e.errors import ImageError

_JPEG_QUALITY = 90


def prepare_key_image(
    image: Image.Image | str | Path | bytes,
    size: tuple[int, int] = DISPLAY_KEY_SIZE,
) -> bytes:
    """Prepare an image for display on a button key.

    Accepts a PIL Image, a file path (str or Path), or raw JPEG bytes.
    When a PIL Image or file path is provided, the image is resized to
    the target dimensions, rotated 270 degrees (the device applies 90 CW),
    and encoded as JPEG.

    When raw bytes are provided, they are returned as-is (assumed to be
    a pre-prepared 60x60 rotated JPEG).

    Args:
        image: Source image — PIL Image, file path, or raw JPEG bytes.
        size: Target dimensions (width, height). Default: (60, 60).

    Returns:
        JPEG-encoded bytes ready to send to the device.

    Raises:
        ImageError: If the image cannot be processed.
    """
    if isinstance(image, bytes):
        return image

    try:
        if isinstance(image, (str, Path)):
            img = Image.open(image)
        elif isinstance(image, Image.Image):
            img = image
        else:
            raise ImageError(
                f"Unsupported image type: {type(image).__name__}. "
                "Expected PIL Image, file path, or raw bytes."
            )

        if img.mode != "RGB":
            img = img.convert("RGB")

        if img.size != size:
            img = img.resize(size, Image.Resampling.LANCZOS)

        img = img.rotate(270)

        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=_JPEG_QUALITY)
        return buf.getvalue()

    except ImageError:
        raise
    except Exception as exc:
        raise ImageError(f"Failed to prepare image: {exc}") from exc
