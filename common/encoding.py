# -*- coding: utf-8 -*-
"""
File encoding auto-detection and conversion.

Strategy (same approach as VS Code / Notepad++ / Notepad):
1. BOM check (UTF-8 / UTF-16 / UTF-32) — authoritative, no guessing.
2. Strict UTF-8 decode — UTF-8 has a strict byte structure, so if it
   decodes cleanly the file IS UTF-8 (or plain ASCII, a UTF-8 subset).
   False positives on real text are practically impossible.
3. charset_normalizer for everything else (CP1251, KOI8-R, Latin-1, ...).
4. Heuristic: if the detector falls back to a "catch-all" encoding
   (latin-1 / iso-8859-1) and the file contains high bytes, prefer
   CP1251 — the de-facto Windows encoding for Russian text.

All files are saved back as UTF-8 (no BOM), so after the first save
the file is in a stable, unambiguous encoding.
"""

import os

try:
    from charset_normalizer import from_bytes
    _HAVE_CHARSET_NORMALIZER = True
except ImportError:  # pragma: no cover
    _HAVE_CHARSET_NORMALIZER = False

# BOM table: (bom_bytes, python_codec) — order matters (UTF-32 before UTF-16).
# Use the BOM-stripping codecs (utf-8-sig / utf-16 / utf-32) so the BOM
# character does not leak into the decoded text.
_BOMS = (
    (b'\xef\xbb\xbf', 'utf-8-sig'),
    (b'\xff\xfe\x00\x00', 'utf-32'),
    (b'\x00\x00\xfe\xff', 'utf-32'),
    (b'\xff\xfe', 'utf-16'),
    (b'\xfe\xff', 'utf-16'),
)

# "Catch-all" encodings: they can decode ANY byte sequence, so a result
# of latin-1/iso-8859-1 on a file with high bytes means "couldn't decide".
_CATCH_ALL = {'latin-1', 'iso-8859-1', 'iso-8859-5'}


def detect_encoding(data: bytes) -> str:
    """Detect the encoding of a byte sequence. Returns a Python codec name."""
    # 1. BOM — authoritative
    for bom, codec in _BOMS:
        if data.startswith(bom):
            return codec

    if not data:
        return 'utf-8'

    # 2. Strict UTF-8 — if it decodes cleanly, it's UTF-8
    try:
        data.decode('utf-8')
        return 'utf-8'
    except UnicodeDecodeError:
        pass

    # 3. charset_normalizer
    if _HAVE_CHARSET_NORMALIZER:
        result = from_bytes(data).best()
        if result is not None:
            enc = str(result.encoding).lower()
            # 4. Heuristic: catch-all result + high bytes → CP1251 (Windows Russian)
            if enc in _CATCH_ALL and any(b > 0x7F for b in data):
                return 'cp1251'
            return enc

    # 5. Fallback (no detector available): assume CP1251 for high-byte files
    if any(b > 0x7F for b in data):
        return 'cp1251'
    return 'utf-8'


def read_text_auto(path: str):
    """
    Read a text file with automatic encoding detection.

    Returns:
        (content, encoding_name, converted)
        - content: decoded text (str)
        - encoding_name: the encoding the file was actually in
        - converted: True if the file was NOT UTF-8 (i.e. it will be
          re-saved as UTF-8, changing the on-disk encoding)
    """
    with open(path, 'rb') as f:
        data = f.read()

    enc = detect_encoding(data)
    try:
        content = data.decode(enc)
    except (UnicodeDecodeError, LookupError):
        # Last resort: never crash on open, replace undecodable bytes
        content = data.decode('utf-8', errors='replace')
        enc = 'utf-8 (replaced)'

    # Defensive: strip a stray BOM char if one slipped through
    if content.startswith('\ufeff'):
        content = content[1:]

    converted = not enc.startswith('utf-8')
    return content, enc, converted


def write_text_utf8(path: str, content: str):
    """Write text as UTF-8 (no BOM)."""
    with open(path, 'w', encoding='utf-8', newline='') as f:
        f.write(content)
