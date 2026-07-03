"""The bridge the UI calls into.

Every write follows the same contract we validated by hand on real saves:
  1. refuse if the game is running
  2. back up the file
  3. write surgically (only the bytes that must change)
  4. re-read from disk and verify the value took AND that no more than the
     expected number of bytes changed
  5. if verification fails, roll back from the backup and report the error

That step 4 guard is what makes the app do exactly what worked manually:
a world-mode flip may change at most 2 bytes, a char_type flip exactly 1.
"""
from __future__ import annotations

from pathlib import Path

from . import __author__, __repo_url__, __version__
from . import locate
from . import saveformat as sf
from . import skills as sk

# Upper bound on bytes a given edit may change. Anything more means something
# unexpected happened and we roll back.
_MAX_WORLD_BYTES = 2
_MAX_CHAR_BYTES = 1


def _count_diff(a: bytes, b: bytes) -> int:
    if len(a) != len(b):
        return max(len(a), len(b))  # any length change is a failure
    return sum(1 for x, y in zip(a, b) if x != y)


class Api:
    def __init__(self) -> None:
        # Set when the user picks a folder manually because auto-detect failed.
        self._root_override = None

    # ---- read side ----

    def get_state(self) -> dict:
        root = self._root_override or locate.save_root()
        worlds = []
        for f in locate.list_worlds(root):
            entry = {"name": f.name, "path": f.path, "size": f.size,
                     "backups": len(locate.list_backups(f.path))}
            try:
                with open(f.path, "rb") as fh:
                    entry["mode"] = sf.read_world_mode(fh.read())
            except Exception as e:
                entry["mode"] = "unknown"
                entry["error"] = str(e)
            worlds.append(entry)

        characters = []
        for f in locate.list_characters(root):
            entry = {"name": f.name, "path": f.path, "size": f.size,
                     "backups": len(locate.list_backups(f.path))}
            try:
                with open(f.path, "rb") as fh:
                    raw = fh.read()
                entry["char_type"] = sf.read_char_type(raw)
                try:
                    entry["skills"] = sk.read_skills(raw)
                except Exception:
                    entry["skills"] = []
            except Exception as e:
                entry["char_type"] = None
                entry["skills"] = []
                entry["error"] = str(e)
            characters.append(entry)

        return {
            "save_dir": str(root) if root else None,
            "game_running": locate.game_is_running(),
            "worlds": worlds,
            "characters": characters,
            "app": {"name": "Dragonscribe", "version": __version__,
                    "author": __author__, "repo_url": __repo_url__},
        }

    # ---- write side ----

    def set_world_mode(self, path: str, mode: str) -> dict:
        return self._guarded_write(
            path, _MAX_WORLD_BYTES,
            transform=lambda data: sf.set_world_mode(data, mode),
            verify=lambda data: sf.read_world_mode(data) == mode,
            label=f"world mode → {mode}",
            result_key="mode",
        )

    def set_char_type(self, path: str, value: int) -> dict:
        value = int(value)
        return self._guarded_write(
            path, _MAX_CHAR_BYTES,
            transform=lambda data: sf.set_char_type(data, value),
            verify=lambda data: sf.read_char_type(data) == value,
            label=f"char_type → {value}",
            result_key="char_type",
        )

    def set_skill_level(self, path: str, guid: str, level: int) -> dict:
        """Set one skill to the XP for the given level (1-99). Verifies that
        only that skill's XP changed and the file stays valid JSON."""
        if locate.game_is_running():
            return {"ok": False, "error": "The game is running. Close it completely first."}
        try:
            level = int(level)
        except (TypeError, ValueError):
            return {"ok": False, "error": "Invalid level."}
        if not 1 <= level <= sk.MAX_LEVEL:
            return {"ok": False, "error": f"Level must be between 1 and {sk.MAX_LEVEL}."}

        new_xp = sk.xp_for_level(level)
        try:
            with open(path, "rb") as fh:
                original = fh.read()
        except OSError as e:
            return {"ok": False, "error": f"Could not read save: {e}"}

        try:
            new_data = sk.set_skill_xp(original, guid, new_xp)
        except Exception as e:
            return {"ok": False, "error": f"Edit failed: {e}"}

        if new_data == original:
            return {"ok": True, "unchanged": True, "level": level,
                    "message": "Already at that level; no change needed."}

        # Semantic guard: only this skill's XP may differ, file must stay valid.
        try:
            if not sk.only_skill_changed(original, new_data, guid, new_xp):
                return {"ok": False, "error": "Refusing to write: change touched more than the one skill."}
        except Exception as e:
            return {"ok": False, "error": f"Refusing to write: could not verify edit ({e})."}

        backup = locate.make_backup(path)
        try:
            with open(path, "wb") as fh:
                fh.write(new_data)
        except OSError as e:
            return {"ok": False, "error": f"Write failed: {e}"}

        with open(path, "rb") as fh:
            on_disk = fh.read()
        try:
            good = sk.only_skill_changed(original, on_disk, guid, new_xp)
        except Exception:
            good = False
        if not good:
            locate.restore_latest_backup(path)
            return {"ok": False, "rolled_back": True,
                    "error": "Verification failed after write; rolled back from backup."}

        return {"ok": True, "level": level, "xp": new_xp, "backup": Path(backup).name}

    def choose_save_folder(self) -> dict:
        """Open a native folder picker so the user can point at their saves
        when the default location can't be found."""
        try:
            import webview
            win = webview.windows[0] if webview.windows else None
            if win is None:
                return {"ok": False, "error": "No window available for the picker."}
            result = win.create_file_dialog(webview.FOLDER_DIALOG)
        except Exception as e:  # noqa: BLE001
            return {"ok": False, "error": f"Could not open the folder picker: {e}"}

        if not result:
            return {"ok": False, "cancelled": True}
        picked = result[0] if isinstance(result, (list, tuple)) else result
        root = locate.resolve_save_root(picked)
        if root is None:
            return {"ok": False,
                    "error": "That folder has no SaveGames or SaveCharacters inside it."}
        self._root_override = root
        return {"ok": True, "save_dir": str(root)}

    def restore_backup(self, path: str) -> dict:
        if locate.game_is_running():
            return {"ok": False, "error": "Close the game before restoring a save."}
        used = locate.restore_latest_backup(path)
        if not used:
            return {"ok": False, "error": "No backup found for this file."}
        return {"ok": True, "restored_from": Path(used).name}

    # ---- internals ----

    def _guarded_write(self, path, max_bytes, *, transform, verify, label, result_key) -> dict:
        if locate.game_is_running():
            return {"ok": False, "error": "The game is running. Close it completely first."}

        try:
            with open(path, "rb") as fh:
                original = fh.read()
        except OSError as e:
            return {"ok": False, "error": f"Could not read save: {e}"}

        try:
            new_data = transform(original)
        except Exception as e:
            return {"ok": False, "error": f"Edit failed: {e}"}

        if new_data == original:
            value = self._safe_read(result_key, original)
            return {"ok": True, "unchanged": True, result_key: value,
                    "message": "Already set; no change needed."}

        changed = _count_diff(original, new_data)
        if changed > max_bytes:
            return {"ok": False, "error":
                    f"Refusing to write: {changed} bytes would change but only "
                    f"{max_bytes} expected for {label}."}

        backup = locate.make_backup(path)
        try:
            with open(path, "wb") as fh:
                fh.write(new_data)
        except OSError as e:
            return {"ok": False, "error": f"Write failed: {e}"}

        # Re-read from disk and verify it actually took.
        with open(path, "rb") as fh:
            on_disk = fh.read()
        if not verify(on_disk) or _count_diff(original, on_disk) > max_bytes:
            locate.restore_latest_backup(path)
            return {"ok": False, "rolled_back": True,
                    "error": f"Verification failed for {label}; rolled back from backup."}

        return {"ok": True, result_key: self._safe_read(result_key, on_disk),
                "backup": Path(backup).name, "bytes_changed": changed}

    @staticmethod
    def _safe_read(result_key, data):
        try:
            if result_key == "mode":
                return sf.read_world_mode(data)
            if result_key == "char_type":
                return sf.read_char_type(data)
        except Exception:
            return None
