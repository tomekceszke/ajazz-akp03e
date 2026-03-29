"""Tests for image preparation."""

from __future__ import annotations

import io
from pathlib import Path

import pytest
from PIL import Image

from ajazz_akp03e._image import prepare_key_image
from ajazz_akp03e.errors import ImageError


class TestPrepareKeyImageRawBytes:
    def test_raw_bytes_passthrough(self) -> None:
        """Raw bytes are returned as-is (assumed pre-prepared)."""
        data = b"\xFF\xD8\xFF\xE0" + b"\x00" * 100
        result = prepare_key_image(data)
        assert result is data


class TestPrepareKeyImage:
    def test_pil_image_returns_jpeg(self) -> None:
        img = Image.new("RGB", (60, 60), (255, 0, 0))
        result = prepare_key_image(img)
        assert result[:2] == b"\xFF\xD8"  # JPEG magic bytes

    def test_pil_image_resized(self) -> None:
        """Non-60x60 images are resized."""
        img = Image.new("RGB", (200, 200), (0, 255, 0))
        result = prepare_key_image(img)
        decoded = Image.open(io.BytesIO(result))
        assert decoded.size == (60, 60)

    def test_pil_image_rotated_270(self) -> None:
        """Image should be rotated 270 degrees."""
        # Create image with red left half, blue right half
        img = Image.new("RGB", (60, 60), (0, 0, 0))
        for x in range(30):
            for y in range(60):
                img.putpixel((x, y), (255, 0, 0))
        for x in range(30, 60):
            for y in range(60):
                img.putpixel((x, y), (0, 0, 255))

        result = prepare_key_image(img)
        decoded = Image.open(io.BytesIO(result))

        # After 270° rotation: left half (red) moves to top half
        top_center = decoded.getpixel((30, 15))
        bottom_center = decoded.getpixel((30, 45))

        assert top_center[0] > 150     # red channel high (was left)
        assert bottom_center[2] > 150  # blue channel high (was right)

    def test_rgba_converted_to_rgb(self) -> None:
        """RGBA images should be converted to RGB."""
        img = Image.new("RGBA", (60, 60), (255, 0, 0, 128))
        result = prepare_key_image(img)
        assert result[:2] == b"\xFF\xD8"

    def test_file_path(self, tmp_path: Path) -> None:
        """File paths should be loaded and processed."""
        path = tmp_path / "test.png"
        img = Image.new("RGB", (60, 60), (0, 0, 255))
        img.save(str(path))

        result = prepare_key_image(str(path))
        assert result[:2] == b"\xFF\xD8"

    def test_pathlib_path(self, tmp_path: Path) -> None:
        """pathlib.Path should work too."""
        path = tmp_path / "test.png"
        img = Image.new("RGB", (60, 60), (0, 0, 255))
        img.save(str(path))

        result = prepare_key_image(path)
        assert result[:2] == b"\xFF\xD8"

    def test_unsupported_type_raises(self) -> None:
        with pytest.raises(ImageError, match="Unsupported"):
            prepare_key_image(12345)  # type: ignore[arg-type]

    def test_nonexistent_file_raises(self) -> None:
        with pytest.raises(ImageError):
            prepare_key_image("/nonexistent/file.jpg")
