"""Skill reading and level editing for character saves.

Skills are stored as a list of {"Id": <guid>, "Xp": <int>} with no level field;
the game derives level from XP at load. So editing a level means writing the
XP threshold for that level. Writes are surgical: we locate the skill by its
unique `"Id": "<guid>"` and replace only the integer after the following
`"Xp":`, leaving CRLF and the rest of the file byte-identical.

The level->XP table and the GUID->name map were built and verified against a
real save (the derived total level matched the in-game total exactly).
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass

MAX_LEVEL = 99

# Cumulative XP required to reach each level. Index == level; index 0 unused.
# Verified against the RuneScape: Dragonwilds wiki and a real save.
LEVEL_XP = [
    0,        # 0 (unused)
    0,        33,       70,       111,      156,      206,      261,      322,      389,      463,       # 1-10
    545,      636,      736,      847,      969,      1104,     1253,     1417,     1598,     1798,      # 11-20
    2018,     2261,     2529,     2825,     3152,     3512,     3910,     4349,     4833,     5367,      # 21-30
    5957,     6608,     7326,     8118,     8993,     9958,     11023,    12199,    13496,    14929,     # 31-40
    16510,    18255,    20181,    22307,    24654,    27245,    30105,    33262,    36747,    40594,     # 41-50
    44581,    48717,    52997,    57421,    61990,    66702,    71560,    76562,    81708,    86998,     # 51-60
    92433,    98012,    103735,   109603,   115616,   121772,   128073,   134518,   141108,   147842,    # 61-70
    154721,   161743,   168910,   176222,   183678,   191278,   199022,   206911,   214944,   223122,    # 71-80
    231444,   239910,   248521,   257276,   266176,   275219,   284407,   293740,   303217,   312838,    # 81-90
    322604,   332514,   342568,   395129,   447689,   543044,   666881,   819200,   1000000,             # 91-99
]
assert len(LEVEL_XP) == MAX_LEVEL + 1


def xp_for_level(level: int) -> int:
    if not 1 <= level <= MAX_LEVEL:
        raise ValueError(f"level out of range: {level}")
    return LEVEL_XP[level]


def level_for_xp(xp: int) -> int:
    lvl = 1
    for level in range(1, MAX_LEVEL + 1):
        if xp >= LEVEL_XP[level]:
            lvl = level
        else:
            break
    return lvl


@dataclass(frozen=True)
class Skill:
    guid: str
    name: str
    category: str


# Order mirrors the in-game categories.
SKILLS: list[Skill] = [
    Skill("4pefO9k1lUqfA6mvHNi1SA", "Attack", "Combat"),
    Skill("0hreSMRVXUihq9qjDO2CFA", "Magic", "Combat"),
    Skill("heq7u88Q2UuLXFqLGTVwQw", "Ranged", "Combat"),
    Skill("jqX0Gh6QI0GFFPCDFK_CJQ", "Mining", "Gathering"),
    Skill("4zYUGF5u_0KbMLkWJmmBbQ", "Woodcutting", "Gathering"),
    Skill("PyUi-0LU_riFY46AnnFiWg", "Farming", "Gathering"),
    Skill("vwY5IkQJJDwb2PKEfoc8MQ", "Fishing", "Gathering"),
    Skill("NOqC-z-2ckqi0El22qMFlw", "Runecrafting", "Artisan"),
    Skill("waK-8EyQFQ2xEjCGYmuTRQ", "Construction", "Artisan"),
    Skill("Wf3i7Ha-B06DH719j1vtBw", "Artisan", "Artisan"),
    Skill("Tn7t6DQyX0-Q0cM5K7B90A", "Cooking", "Artisan"),
]
_BY_GUID = {s.guid: s for s in SKILLS}


class SkillNotFound(Exception):
    """The skill GUID wasn't present exactly once in the file."""


def _skills_entries(data: dict) -> list:
    """Return the list of {Id, Xp} skill records, wherever they live.

    Current saves nest the character payload under `GameProgress`; the field
    was top-level in an earlier layout, so we check both.
    """
    for container in (data.get("GameProgress"), data):
        if isinstance(container, dict):
            node = container.get("Skills")
            if isinstance(node, dict) and isinstance(node.get("Skills"), list):
                return node["Skills"]
    return []


def read_skills(raw: bytes) -> list[dict]:
    """Return the character's skills as UI-ready dicts, in SKILLS order.
    Any unrecognized skill in the file is appended with its GUID as the name."""
    data = json.loads(raw.decode("utf-8"))
    entries = _skills_entries(data)
    xp_by_guid = {e.get("Id"): e.get("Xp", 0) for e in entries}

    out = []
    for s in SKILLS:
        if s.guid in xp_by_guid:
            xp = xp_by_guid[s.guid]
            out.append({"guid": s.guid, "name": s.name, "category": s.category,
                        "xp": xp, "level": level_for_xp(xp)})
    # Surface anything we don't recognize so it's never silently hidden.
    for guid, xp in xp_by_guid.items():
        if guid not in _BY_GUID:
            out.append({"guid": guid, "name": guid, "category": "Unknown",
                        "xp": xp, "level": level_for_xp(xp)})
    return out


def set_skill_xp(raw: bytes, guid: str, new_xp: int) -> bytes:
    """Surgically replace the XP for one skill. Only the integer changes."""
    needle = b'"Id": "' + guid.encode("ascii") + b'"'
    if raw.count(needle) != 1:
        raise SkillNotFound(f"skill id not found exactly once: {guid}")
    gpos = raw.find(needle)
    xpos = raw.find(b'"Xp":', gpos)
    if xpos == -1:
        raise SkillNotFound(f"no Xp after skill id: {guid}")
    m = re.compile(rb'("Xp":\s*)(\d+)').match(raw, xpos)
    if not m:
        raise SkillNotFound(f"malformed Xp for skill: {guid}")
    start, end = m.span(2)
    return raw[:start] + str(new_xp).encode("ascii") + raw[end:]


def only_skill_changed(before: bytes, after: bytes, guid: str, new_xp: int) -> bool:
    """True iff `after` equals `before` with exactly the one skill's XP set to
    new_xp and nothing else in the document touched."""
    b = json.loads(before.decode("utf-8"))
    a = json.loads(after.decode("utf-8"))
    for e in _skills_entries(b):
        if e.get("Id") == guid:
            e["Xp"] = new_xp
            break
    else:
        return False
    return b == a
