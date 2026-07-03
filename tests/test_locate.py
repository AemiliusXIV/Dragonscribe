"""Tests for save discovery and folder resolution."""
from dragonscribe import locate
from dragonscribe.api import Api


def test_resolve_save_root_direct(tmp_path):
    (tmp_path / "SaveGames").mkdir()
    assert locate.resolve_save_root(tmp_path) == tmp_path


def test_resolve_save_root_parent_with_saved(tmp_path):
    saved = tmp_path / "Saved"
    (saved / "SaveCharacters").mkdir(parents=True)
    assert locate.resolve_save_root(tmp_path) == saved


def test_resolve_save_root_rejects_unrelated(tmp_path):
    (tmp_path / "random").mkdir()
    assert locate.resolve_save_root(tmp_path) is None


def test_resolve_save_root_missing_path(tmp_path):
    assert locate.resolve_save_root(tmp_path / "nope") is None


def test_discovery_skips_non_saves(tmp_path):
    games = tmp_path / "SaveGames"
    games.mkdir()
    (games / "Dawn.sav").write_bytes(b"x")
    (games / "Dawn.sav.backup").write_bytes(b"x")
    (games / "EnhancedInputUserSettings.sav").write_bytes(b"x")
    (games / "steam_autocloud.vdf").write_bytes(b"x")
    worlds = locate.list_worlds(tmp_path)
    assert [w.name for w in worlds] == ["Dawn.sav"]


def test_api_override_drives_get_state(tmp_path):
    (tmp_path / "SaveGames").mkdir()
    (tmp_path / "SaveCharacters").mkdir()
    api = Api()
    api._root_override = tmp_path
    state = api.get_state()
    assert state["save_dir"] == str(tmp_path)
    assert state["worlds"] == []
    assert state["characters"] == []
