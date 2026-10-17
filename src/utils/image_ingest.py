"""Validation and normalization of uploaded cap photos."""

import io

from PIL import Image, ImageOps, UnidentifiedImageError

NORMALIZED_CONTENT_TYPE = "image/jpeg"
JPEG_QUALITY = 90
# Rejects absurd dimensions before decoding the pixels (~80 MP).
MAX_PIXELS = 80_000_000


class InvalidImageError(ValueError):
    """Raised when uploaded bytes are not a decodable image."""


def normalize_image(data: bytes, max_side: int) -> bytes:
    """Decodes an uploaded image and re-encodes it as a JPEG.

    Applies the EXIF orientation (phone photos are often stored rotated),
    converts to RGB and downscales so the longest side is at most ``max_side``.

    Args:
        data: Raw uploaded bytes.
        max_side: Maximum width/height of the stored image, in pixels.

    Returns:
        The normalized JPEG bytes.

    Raises:
        InvalidImageError: If the bytes are not an image Pillow can decode,
            or the image is unreasonably large.
    """
    try:
        with Image.open(io.BytesIO(data)) as img:
            if img.width * img.height > MAX_PIXELS:
                raise InvalidImageError("Image dimensions are too large.")
            img.load()
            normalized = ImageOps.exif_transpose(img).convert("RGB")
    except InvalidImageError:
        raise
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as e:
        raise InvalidImageError(
            "Unsupported or corrupt image. Use a JPEG, PNG or WebP photo."
        ) from e

    normalized.thumbnail((max_side, max_side), Image.Resampling.LANCZOS)
    out = io.BytesIO()
    normalized.save(out, format="JPEG", quality=JPEG_QUALITY, optimize=True)
    return out.getvalue()
