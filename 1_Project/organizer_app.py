"""
Organizer 2.8 - organizer_app.py: starts the desktop app (double-click app.bat).

  python organizer_app.py            open the window
  python organizer_app.py --tray     start hidden in the tray (when pystray + pillow are installed)
  python organizer_app.py --selftest check this PC (Python, Tkinter, tray packages, your settings and history
                                     folders) and print a plain report; nothing is changed

If the window cannot start, you get a clear message and a file with the details instead of a window that
silently disappears: <your data folder>/startup_error.txt
"""
import atexit
import os
import sys
import traceback
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
TITLE = "Organizer 2.8"


def message_box(text):
    """Show a message even when there is no console and no Tkinter."""
    if sys.platform.startswith("win") and not os.environ.get("ORGANIZER_APP_NO_DIALOG"):
        try:
            import ctypes
            ctypes.windll.user32.MessageBoxW(0, text, TITLE, 0x10)
            return
        except Exception:
            pass
    print(text, file=sys.stderr)


def data_folder():
    import organizer
    return organizer.data_dir()


def selftest():
    """Returns (report text, everything ok). Never changes your settings or files."""
    lines, ok = [f"{TITLE} - self-test", ""], True

    def good(text):
        lines.append("  [OK] " + text)

    def bad(text, fix):
        nonlocal ok
        ok = False
        lines.append("  [!!] " + text)
        lines.append("       fix: " + fix)

    def note(text):
        lines.append("  [..] " + text)

    if sys.version_info < (3, 8):
        bad(f"Python {sys.version.split()[0]} is too old", "install Python 3.10 or newer from python.org")
    else:
        good(f"Python {sys.version.split()[0]}")
    try:
        import organizer
        good(f"engine {organizer.__version__} in {organizer.SCRIPT_DIR}")
        folder = organizer.data_dir()
        folder.mkdir(parents=True, exist_ok=True)
        probe = folder / ".selftest"
        probe.write_text("ok")
        probe.unlink()
        good(f"your data folder is writable: {folder}")
        history = organizer.history_dir()
        if history is None:
            bad("no writable history folder", f"make {folder / 'history'} writable (or set ORGANIZER_HOME to another folder)")
        else:
            good(f"undo history: {history}")
        good(f"settings in use: {organizer.active_config_path()}"
             + ("" if organizer.active_config_path().exists() else "  (created on first start)"))
    except Exception as exc:
        bad(f"the engine could not start: {exc}", "run repair.bat, or copy organizer.py again from the download")
    try:
        import app_backend
        presets = app_backend.Backend().list_presets()
        (good if len(presets) >= 7 else lambda t: bad(t, "copy the presets folder again from the download"))(
            f"{len(presets)} ways of organizing found")
    except Exception as exc:
        bad(f"the app logic could not start: {exc}", "run repair.bat")
    try:
        import tkinter
        root = tkinter.Tk()
        root.withdraw()
        root.destroy()
        good(f"Tkinter {tkinter.TkVersion} works (windows can be shown)")
    except Exception as exc:
        bad(f"windows cannot be shown: {exc}",
            "re-run the Python installer and tick 'tcl/tk and IDLE'. (On a machine with no screen this is normal.)")
    try:
        import pystray
        import PIL
        good("tray icon packages are installed")
    except Exception:
        note("tray icon packages are not installed (optional): run  pip install pystray pillow")
    try:
        import organizer
        task = organizer.scheduled_task_info() if hasattr(organizer, "scheduled_task_info") else None
        if sys.platform.startswith("win"):
            note("background task: run doctor.bat to check it")
    except Exception:
        pass
    lines += ["", "Everything looks fine." if ok else "Something needs attention (see [!!] above).",
              "Questions? Send this report."]
    return "\n".join(lines), ok


def single_instance():
    """True if this is the only copy. A leftover lock from a crash does not count."""
    import organizer
    lock = organizer.data_dir() / "app.lock"
    try:
        other = int(lock.read_text().strip())
        if other != os.getpid() and organizer._pid_alive(other):
            return False
    except (OSError, ValueError):
        pass
    try:
        lock.parent.mkdir(parents=True, exist_ok=True)
        lock.write_text(str(os.getpid()))
        atexit.register(lambda: lock.unlink() if lock.exists() and lock.read_text().strip() == str(os.getpid()) else None)
    except OSError:
        pass
    return True


def make_dpi_aware():
    """Crisp text on high-resolution Windows screens."""
    if not sys.platform.startswith("win"):
        return
    try:
        import ctypes
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except Exception:
            ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass


def write_error_file(exc):
    try:
        path = data_folder() / "startup_error.txt"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"{TITLE} could not start\n\n{traceback.format_exc()}", encoding="utf-8")
        return path
    except Exception:
        return None


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if "--selftest" in argv:
        text, ok = selftest()
        print(text)
        try:
            (data_folder() / "selftest.txt").write_text(text, encoding="utf-8")
        except Exception:
            pass
        return 0 if ok else 1
    try:
        if not single_instance():
            message_box("Organizer is already running. Look for its icon in the tray or on the taskbar.")
            return 0
        if os.environ.get("ORGANIZER_APP_TEST_CRASH"):          # test hooks: no window, no Tkinter needed
            raise RuntimeError("test crash")
        if os.environ.get("ORGANIZER_APP_NO_GUI"):
            print("ready")
            return 0
        try:
            import tkinter  # noqa: F401
        except Exception as exc:
            message_box("The window cannot start because Tkinter is missing or broken:\n"
                        f"{exc}\n\nRe-run the Python installer and tick 'tcl/tk and IDLE'.\n"
                        "You can still use the command line:  python organizer.py --help")
            return 1
        make_dpi_aware()
        import app_window
        app_window.App(start_hidden="--tray" in argv).run()
        return 0
    except Exception as exc:
        path = write_error_file(exc)
        message_box(f"{TITLE} could not start:\n{exc}\n\n"
                    + (f"Details were saved in:\n{path}" if path else "Run  python organizer_app.py --selftest  for a check."))
        return 1


if __name__ == "__main__":
    sys.exit(main())
