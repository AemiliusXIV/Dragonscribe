"""Byte-level read/write for RuneScape: Dragonwilds save files.

Covers the two operations Dragonscribe performs:
  - world mode classification (standard / hard / custom) in the binary .sav
  - the character `char_type` flag in the JSON character file

Writes are surgical: only the bytes that actually change are touched, so the
rest of the file stays identical to what the game wrote. The save format was
reverse engineered by the community; see NOTICE for credit.
"""
from __future__ import annotations

import struct
from dataclasses import dataclass

# World mode is stored in two places that must agree for the game to accept it:
#   1. a uint32 enum at the first "L_World\0" + 9
#   2. the first byte of the CustomDifficultySettings field inside the
#      WorldSaveSettings PROP chunk
# Each mode is the pair (enum value, cds byte).
_MODE_BYTES = {
    "standard": (0, 0x00),
    "hard":     (1, 0x01),
    "custom":   (3, 0x03),
}
_BYTES_TO_MODE = {v: k for k, v in _MODE_BYTES.items()}

# The WorldSaveSettings PROP carries a 13-entry offset table whose first three
# entries are always these values. Other PROP chunks in the file (entity
# records) do not match, which is how we pick the right one.
_WSS_PROP_FIELD_COUNT = 13
_WSS_PROP_SIGNATURE = (0x0, 0x4, 0x14)
_CDS_FIELD_INDEX = 8  # CustomDifficultySettings position in the offset table


class ModeBytesNotFound(Exception):
    """The mode bytes could not be located in the save."""


@dataclass(frozen=True)
class ModeLocation:
    enum_offset: int   # absolute offset of the L_World uint32 enum
    cds_offset: int    # absolute offset of the CustomDifficultySettings byte


def _find_wss_prop(data: bytes) -> int:
    """Return the offset of the WorldSaveSettings PROP, or -1."""
    pos = 0
    while True:
        pos = data.find(b"PROP", pos)
        if pos == -1:
            return -1
        try:
            count = struct.unpack_from("<I", data, pos + 8)[0]
            if count == _WSS_PROP_FIELD_COUNT:
                offsets = struct.unpack_from(f"<{count}I", data, pos + 12)
                if offsets[:3] == _WSS_PROP_SIGNATURE:
                    return pos
        except struct.error:
            pass
        pos += 4


def locate_mode_bytes(data: bytes) -> ModeLocation:
    """Find the two world-mode byte positions. Raises if either is missing."""
    lw = data.find(b"L_World\x00")
    if lw == -1:
        raise ModeBytesNotFound("L_World marker not present")

    prop = _find_wss_prop(data)
    if prop == -1:
        raise ModeBytesNotFound("WorldSaveSettings PROP not found")

    count = struct.unpack_from("<I", data, prop + 8)[0]
    offsets = struct.unpack_from(f"<{count}I", data, prop + 12)
    cds = prop + 12 + count * 4 + offsets[_CDS_FIELD_INDEX]
    return ModeLocation(enum_offset=lw + 9, cds_offset=cds)


def read_world_mode(data: bytes) -> str:
    """Return 'standard', 'hard', 'custom', or 'mixed (...)' for diagnostics."""
    loc = locate_mode_bytes(data)
    enum = struct.unpack_from("<I", data, loc.enum_offset)[0]
    cds = data[loc.cds_offset]
    mode = _BYTES_TO_MODE.get((enum, cds))
    if mode:
        return mode
    return f"mixed (enum={enum}, cds=0x{cds:02x})"


def set_world_mode(data: bytes, target: str) -> bytes:
    """Return a copy of `data` with the world mode set to `target`.

    Only the two mode bytes change; every other byte is preserved.
    """
    if target not in _MODE_BYTES:
        raise ValueError(f"unknown mode: {target!r}")
    enum_val, cds_val = _MODE_BYTES[target]
    loc = locate_mode_bytes(data)
    out = bytearray(data)
    struct.pack_into("<I", out, loc.enum_offset, enum_val)
    out[loc.cds_offset] = cds_val
    return bytes(out)


# --- character char_type (JSON file, but edited as raw bytes to keep the
#     game's CRLF line endings and formatting byte-for-byte intact) ---

CHAR_TYPE_STANDARD = 0
CHAR_TYPE_CUSTOM = 3


class CharTypeNotFound(Exception):
    """The char_type field could not be located exactly once."""


def read_char_type(raw: bytes) -> int:
    for value in (0, 1, 2, 3):
        if raw.count(b'"char_type": %d' % value) == 1:
            return value
    raise CharTypeNotFound("char_type not found or ambiguous")


def set_char_type(raw: bytes, target: int) -> bytes:
    """Return a copy of the character file with char_type set to `target`.

    Exactly one byte changes. Raises if the field is missing or appears more
    than once (so we never edit blindly).
    """
    current = read_char_type(raw)
    if current == target:
        return raw
    needle = b'"char_type": %d' % current
    if raw.count(needle) != 1:
        raise CharTypeNotFound(f"expected one char_type, found {raw.count(needle)}")
    return raw.replace(needle, b'"char_type": %d' % target)
