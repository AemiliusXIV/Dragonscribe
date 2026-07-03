"""Tests for the skills module: XP table, level math, surgical XP edits."""
import json

import pytest

from dragonscribe import skills as sk

ATTACK = "4pefO9k1lUqfA6mvHNi1SA"
COOKING = "Tn7t6DQyX0-Q0cM5K7B90A"

# A character blob with CRLF line endings, like the game writes.
CHAR = (
    '{\r\n\t"Skills":\r\n\t{\r\n\t\t"Skills": [\r\n'
    '\t\t\t{\r\n\t\t\t\t"Id": "' + ATTACK + '",\r\n\t\t\t\t"Xp": 261\r\n\t\t\t},\r\n'
    '\t\t\t{\r\n\t\t\t\t"Id": "' + COOKING + '",\r\n\t\t\t\t"Xp": 882\r\n\t\t\t}\r\n'
    '\t\t]\r\n\t}\r\n}'
).encode("utf-8")


def test_level_xp_known_values():
    assert sk.xp_for_level(1) == 0
    assert sk.xp_for_level(7) == 261
    assert sk.xp_for_level(14) == 847
    assert sk.xp_for_level(51) == 44581
    assert sk.xp_for_level(99) == 1_000_000


def test_level_for_xp_boundaries():
    assert sk.level_for_xp(0) == 1
    assert sk.level_for_xp(260) == 6
    assert sk.level_for_xp(261) == 7
    assert sk.level_for_xp(262) == 7
    assert sk.level_for_xp(846) == 13
    assert sk.level_for_xp(847) == 14
    assert sk.level_for_xp(1_000_000) == 99
    assert sk.level_for_xp(5_000_000) == 99


def test_xp_for_level_out_of_range():
    for bad in (0, 100, -1):
        with pytest.raises(ValueError):
            sk.xp_for_level(bad)


def test_read_skills_order_and_levels():
    got = sk.read_skills(CHAR)
    names = [s["name"] for s in got]
    assert names == ["Attack", "Cooking"]  # SKILLS order, only present ones
    attack = next(s for s in got if s["name"] == "Attack")
    assert attack["level"] == 7 and attack["xp"] == 261


def test_set_skill_xp_surgical():
    out = sk.set_skill_xp(CHAR, ATTACK, 1_000_000)
    # only the digits changed; CRLF preserved
    assert out.count(b"\r\n") == CHAR.count(b"\r\n")
    a = json.loads(out.decode("utf-8"))["Skills"]["Skills"]
    by = {e["Id"]: e["Xp"] for e in a}
    assert by[ATTACK] == 1_000_000
    assert by[COOKING] == 882  # untouched


def test_set_skill_xp_unknown_guid():
    with pytest.raises(sk.SkillNotFound):
        sk.set_skill_xp(CHAR, "nope", 100)


def test_only_skill_changed_true():
    out = sk.set_skill_xp(CHAR, COOKING, sk.xp_for_level(99))
    assert sk.only_skill_changed(CHAR, out, COOKING, 1_000_000)


def test_only_skill_changed_false_when_other_touched():
    out = sk.set_skill_xp(CHAR, COOKING, sk.xp_for_level(99))
    # claim it was the Attack skill that changed -> should be False
    assert not sk.only_skill_changed(CHAR, out, ATTACK, sk.xp_for_level(99))
