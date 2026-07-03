"""Unit tests for the byte logic, using synthetic fixtures so CI needs no real
save files. The fixtures reproduce the exact structures the parser keys on:
the L_World enum and the WorldSaveSettings PROP offset table.
"""
import struct

import pytest

from dragonscribe import saveformat as sf


def make_world(enum: int, cds: int) -> bytes:
    """Build a minimal blob with a locatable L_World enum and WSS PROP."""
    # L_World marker; enum uint32 sits at marker+9 (one filler byte after the null).
    head = b"L_World\x00" + b"\x00" + struct.pack("<I", enum)
    head += b"\x00" * 16  # padding so offsets don't collide with the marker

    # WorldSaveSettings PROP: 13 offsets, signature 0,4,0x14; CDS at index 8.
    offsets = [0, 4, 0x14, 0x20, 0x30, 0x40, 0x41, 0x42, 0x50, 0x60, 0x70, 0x80, 0x90]
    body = struct.pack("<13I", *offsets)
    data_region = bytearray(0xA0)
    data_region[offsets[8]] = cds
    prop = b"PROP" + struct.pack("<I", len(body) + len(data_region)) + struct.pack("<I", 13) + body + bytes(data_region)

    # A decoy PROP earlier in the file (wrong field count) must be ignored.
    decoy = b"PROP" + struct.pack("<I", 8) + struct.pack("<I", 2) + struct.pack("<2I", 0, 4)
    return decoy + head + prop


@pytest.mark.parametrize("mode,enum,cds", [
    ("standard", 0, 0x00),
    ("hard", 1, 0x01),
    ("custom", 3, 0x03),
])
def test_read_world_mode(mode, enum, cds):
    assert sf.read_world_mode(make_world(enum, cds)) == mode


def test_set_world_mode_is_two_bytes():
    data = make_world(1, 0x01)  # hard
    out = sf.set_world_mode(data, "custom")
    assert len(out) == len(data)
    diff = [i for i in range(len(data)) if data[i] != out[i]]
    assert len(diff) == 2
    assert sf.read_world_mode(out) == "custom"


def test_world_mode_round_trip_restores_bytes():
    data = make_world(0, 0x00)  # standard
    there = sf.set_world_mode(data, "custom")
    back = sf.set_world_mode(there, "standard")
    assert back == data


def test_decoy_prop_ignored():
    # The earlier 2-field PROP must not be mistaken for WorldSaveSettings.
    data = make_world(3, 0x03)
    loc = sf.locate_mode_bytes(data)
    # CDS offset must land past the decoy and the real PROP header.
    assert data[loc.cds_offset] == 0x03


def test_set_world_mode_rejects_unknown():
    with pytest.raises(ValueError):
        sf.set_world_mode(make_world(0, 0), "nightmare")


def test_missing_markers_raise():
    with pytest.raises(sf.ModeBytesNotFound):
        sf.read_world_mode(b"no markers here")


# --- char_type ---

CHAR = b'{\r\n\t"meta_data": {\r\n\t\t"char_name": "Test",\r\n\t\t"char_type": 0\r\n\t}\r\n}'


def test_read_char_type():
    assert sf.read_char_type(CHAR) == 0


def test_set_char_type_one_byte_crlf_preserved():
    out = sf.set_char_type(CHAR, 3)
    diff = [i for i in range(len(CHAR)) if CHAR[i] != out[i]]
    assert len(diff) == 1
    assert sf.read_char_type(out) == 3
    assert out.count(b"\r\n") == CHAR.count(b"\r\n")


def test_set_char_type_noop():
    assert sf.set_char_type(CHAR, 0) == CHAR


def test_char_type_round_trip():
    assert sf.set_char_type(sf.set_char_type(CHAR, 3), 0) == CHAR


def test_ambiguous_char_type_raises():
    doubled = CHAR + b'\r\n"char_type": 0'
    with pytest.raises(sf.CharTypeNotFound):
        sf.read_char_type(doubled)
