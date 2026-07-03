"""Finding saves, detecting the running game, and making backups.

Everything here is filesystem plumbing around the byte logic in saveformat.py.
The hard rule: never write to a save while the game is running, and always
keep a timestamped copy before touching anything.
"""
from __future__ import annotations

import os
import shutil
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

# The game stores saves under %LOCALAPPDATA%\RSDragonwilds\Saved.
SAVE_ROOT_ENV = "RSDW_SAVE_DIR"  # optional override, mostly for testing
_DEFAULT_REL = Path("RSDragonwilds") / "Saved"

# Files that live in the save folders but aren't player saves.
_SKIP_WORLD = {"enhancedinputusersettings.sav"}
_SKIP_EXT = {".backup", ".verbackup", ".bak", ".vdf", ".tmp"}

BACKUP_DIRNAME = "editor_backups"

# A process is treated as "the game" if its lowercased name contains any of
# these. Kept deliberately narrow to avoid false positives.
GAME_PROCESS_HINTS = ("dragonwilds", "rsdragon")


@dataclass
class SaveFile:
    name: str
    path: str
    size: int


def save_root() -> Path | None:
    override = os.environ.get(SAVE_ROOT_ENV)
    if override and os.path.isdir(override):
        return Path(override)
    local = os.environ.get("LOCALAPPDATA")
    if local:
        candidate = Path(local) / _DEFAULT_REL
        if candidate.is_dir():
            return candidate
    return None


def resolve_save_root(path: str | Path) -> Path | None:
    """Given a user-picked folder, return the actual save root (the one holding
    SaveGames/SaveCharacters), or None if it doesn't look like one.

    Accepts either the `Saved` folder itself or a parent that contains it.
    """
    p = Path(path)
    if not p.is_dir():
        return None
    if (p / "SaveGames").is_dir() or (p / "SaveCharacters").is_dir():
        return p
    nested = p / "Saved"
    if nested.is_dir() and ((nested / "SaveGames").is_dir() or (nested / "SaveCharacters").is_dir()):
        return nested
    return None


def _list(folder: Path, *, is_world: bool) -> list[SaveFile]:
    if not folder.is_dir():
        return []
    out = []
    for entry in sorted(folder.iterdir()):
        if not entry.is_file():
            continue
        low = entry.name.lower()
        ext = entry.suffix.lower()
        if ext in _SKIP_EXT:
            continue
        if is_world:
            if ext != ".sav" or low in _SKIP_WORLD:
                continue
        else:
            if ext != ".json":
                continue
        out.append(SaveFile(entry.name, str(entry), entry.stat().st_size))
    return out


def list_worlds(root: Path | None = None) -> list[SaveFile]:
    root = root or save_root()
    if not root:
        return []
    return _list(root / "SaveGames", is_world=True)


def list_characters(root: Path | None = None) -> list[SaveFile]:
    root = root or save_root()
    if not root:
        return []
    return _list(root / "SaveCharacters", is_world=False)


def game_is_running() -> bool:
    try:
        import psutil
    except ImportError:
        return False
    for proc in psutil.process_iter(["name"]):
        name = (proc.info.get("name") or "").lower()
        if any(hint in name for hint in GAME_PROCESS_HINTS):
            return True
    return False


def make_backup(path: str) -> str:
    """Copy `path` into its editor_backups folder with a timestamp. Returns
    the backup path."""
    src = Path(path)
    backup_dir = src.parent / BACKUP_DIRNAME
    backup_dir.mkdir(exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    dest = backup_dir / f"{src.name}.{stamp}.bak"
    shutil.copy2(src, dest)
    return str(dest)


def list_backups(path: str) -> list[str]:
    """Newest-first list of backups for a given save file."""
    src = Path(path)
    backup_dir = src.parent / BACKUP_DIRNAME
    if not backup_dir.is_dir():
        return []
    prefix = src.name + "."
    found = [p for p in backup_dir.iterdir() if p.name.startswith(prefix) and p.suffix == ".bak"]
    return [str(p) for p in sorted(found, key=lambda p: p.stat().st_mtime, reverse=True)]


def restore_latest_backup(path: str) -> str | None:
    """Copy the newest backup back over the original. Returns the backup used."""
    backups = list_backups(path)
    if not backups:
        return None
    shutil.copy2(backups[0], path)
    return backups[0]
