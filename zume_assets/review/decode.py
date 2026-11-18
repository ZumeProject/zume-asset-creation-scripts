"""QR PNG decode backends (zxing-cpp preferred; pyzbar optional)."""

from __future__ import annotations

from pathlib import Path


class QrDecodeError(RuntimeError):
    """Raised when no decode backend is installed or decode fails hard."""


def _import_ok(module: str) -> bool:
    try:
        __import__(module)
        return True
    except ImportError:
        return False


def backend_name() -> str:
    if _import_ok("zxingcpp"):
        return "zxing-cpp"
    if _import_ok("pyzbar"):
        return "pyzbar"
    return "none"


def _decode_zxing(path: Path) -> str:
    import zxingcpp  # type: ignore[import-untyped]
    from PIL import Image

    image = Image.open(path).convert("RGB")
    results = zxingcpp.read_barcodes(image)
    for result in results:
        text = getattr(result, "text", None) or ""
        if text:
            return str(text)
    return ""


def _decode_pyzbar(path: Path) -> str:
    from PIL import Image
    from pyzbar.pyzbar import decode as pyzbar_decode  # type: ignore[import-untyped]

    image = Image.open(path)
    results = pyzbar_decode(image)
    for result in results:
        raw = result.data
        if isinstance(raw, bytes):
            return raw.decode("utf-8", errors="replace")
        if raw:
            return str(raw)
    return ""


def decode_qr_png(path: Path) -> str:
    """Decode a QR PNG to its payload string.

    Tries zxing-cpp, then pyzbar. Empty string means image opened but no QR found.
    Raises QrDecodeError if no backend is installed.
    """
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(f"QR PNG not found: {path}")

    backends: list[tuple[str, object]] = []
    if _import_ok("zxingcpp"):
        backends.append(("zxing-cpp", _decode_zxing))
    if _import_ok("pyzbar"):
        backends.append(("pyzbar", _decode_pyzbar))
    if not backends:
        raise QrDecodeError(
            "No QR decode backend installed. Install with: pip install -e '.[review]' "
            "(zxing-cpp) or add pyzbar + system libzbar."
        )

    errors: list[str] = []
    for name, fn in backends:
        try:
            return fn(path)  # type: ignore[operator]
        except Exception as exc:  # noqa: BLE001 — try next backend
            errors.append(f"{name}: {exc}")
    raise QrDecodeError(f"Failed to decode QR image {path}: {'; '.join(errors)}")
