"""Desktop window bootstrap.

Wraps the local HTML UI in a native window via pywebview (WebView2 on
Windows). No web server, no browser tab, no open port.
"""
from __future__ import annotations

import sys
from pathlib import Path

import webview

from . import __version__
from .api import Api


def _ui_path() -> str:
    # When frozen by PyInstaller, data files live under sys._MEIPASS.
    here = Path(__file__).resolve().parent
    meipass = Path(getattr(sys, "_MEIPASS", here))
    # Frozen bundle keeps the package path under _MEIPASS; source tree uses here.
    for candidate in (
        meipass / "dragonscribe" / "ui" / "index.html",
        meipass / "ui" / "index.html",
        here / "ui" / "index.html",
    ):
        if candidate.exists():
            return str(candidate)
    raise FileNotFoundError("Dragonscribe UI not found (ui/index.html)")


def _selfcheck_report(line: str) -> None:
    # Windowed builds have no console, so also drop a file next to the exe.
    try:
        sys.stdout.write(line + "\n")
        sys.stdout.flush()
    except Exception:
        pass
    try:
        out = Path(sys.executable).resolve().parent / "selfcheck.txt"
        out.write_text(line + "\n", encoding="utf-8")
    except Exception:
        pass


def main() -> None:
    if "--selfcheck" in sys.argv:
        # Headless sanity check for CI and the frozen build: resolve the UI,
        # exercise the API, then exit via a code. Catches everything so a
        # windowed build never pops a blocking error dialog.
        try:
            ui = _ui_path()
            state = Api().get_state()
            line = (f"selfcheck ok: ui={ui} worlds={len(state['worlds'])} "
                    f"characters={len(state['characters'])} version={__version__}")
            _selfcheck_report(line)
            sys.exit(0)
        except Exception as e:  # noqa: BLE001 - we want the exit code, not a dialog
            _selfcheck_report(f"selfcheck FAILED: {e}")
            sys.exit(1)

    api = Api()
    webview.create_window(
        f"Dragonscribe {__version__}",
        url=_ui_path(),
        js_api=api,
        width=940,
        height=760,
        min_size=(760, 560),
    )
    webview.start()


if __name__ == "__main__":
    main()
