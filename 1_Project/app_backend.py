"""
Organizer 2.8 - app_backend.py: everything the desktop app does, without any windows.

The window (organizer_app.py) only shows and collects things; the work happens here, so it can be tested
without a screen. Each Windows user gets a private data folder (settings + undo history), so several people
can share one PC - and one copy of the program - and each organizes in their own way.
"""
import contextlib
import copy
import io
import json
import logging
import logging.handlers
import os
import re
import shutil
import sys
import tempfile
import time
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace

import organizer

APP_DIR = Path(getattr(sys, "_MEIPASS", None) or Path(__file__).resolve().parent)
PRESET_DIR = APP_DIR / "presets"
DAY_FORMAT = "%Y%m%d-%H%M%S"


class BackendError(Exception):
    """A problem with a plain-language message that can be shown to the user as it is."""

    def __init__(self, message, kind="error"):
        super().__init__(message)
        self.kind = kind


default_data_dir = organizer.default_data_dir      # one rule for the app, the command line and the scheduled task


class _Capture(logging.Handler):
    def __init__(self):
        super().__init__(logging.INFO)
        self.lines = []

    def emit(self, record):
        try:
            self.lines.append(record.getMessage())
        except Exception:
            pass


@contextlib.contextmanager
def _capturing():
    """Collect everything the engine logs or prints while the block runs."""
    handler, out = _Capture(), io.StringIO()
    old_level = organizer.log.level
    organizer.log.addHandler(handler)
    organizer.log.setLevel(logging.INFO)
    try:
        with contextlib.redirect_stdout(out):
            yield handler, out
    finally:
        organizer.log.removeHandler(handler)
        organizer.log.setLevel(old_level)


PLAN_LINE = re.compile(r"^(?:\[dry-run\] )?(.+?) -> (.+?)  \[(.+)\]$")


class Backend:
    def __init__(self, data_dir=None):
        if data_dir:
            organizer.DATA_DIR = Path(data_dir)
        organizer.history_dir.cache_clear()               # the engine remembers its history folder: look again
        self.data_dir = organizer.data_dir()
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self._use()
        self.config_path = organizer.active_config_path()
        self.settings_path = self.data_dir / "app_settings.json"
        self._attach_file_log()
        self.first_run = not self.config_path.exists()
        if self.first_run:
            if self._old_install_in_use():
                organizer.ensure_user_config()           # keep the watched folders of an existing install
                self.first_run = False
            else:
                self._write_config(self.build_preset_config("standard"))

    @staticmethod
    def _old_install_in_use():
        """An install made before 2.8 keeps its settings next to the program; carry them over if it watches folders."""
        old = organizer.SCRIPT_DIR / "organizer_config.json"
        try:
            return bool(json.loads(old.read_text(encoding="utf-8-sig")).get("watch"))
        except (OSError, ValueError, AttributeError):
            return False

    def _use(self):
        if organizer.DATA_DIR != self.data_dir:
            organizer.DATA_DIR = self.data_dir
            organizer.history_dir.cache_clear()       # the engine remembers the folder; point it at this user's

    # ------------------------------------------------------------------ plumbing
    def _attach_file_log(self):
        old = getattr(organizer.log, "_app_file_handler", None)
        if old is not None:
            if getattr(organizer.log, "_app_file_handler_dir", None) == self.data_dir:
                return
            organizer.log.removeHandler(old)                # another user's folder: log to this one instead
            old.close()
            organizer.log._app_file_handler = None
        try:
            folder = self.data_dir / "history"
            folder.mkdir(parents=True, exist_ok=True)
            handler = logging.handlers.RotatingFileHandler(folder / "organizer.log", maxBytes=1_000_000,
                                                           backupCount=3, encoding="utf-8")
            handler.setFormatter(logging.Formatter("%(asctime)s  %(levelname)-7s %(message)s", "%Y-%m-%d %H:%M:%S"))
            handler.addFilter(organizer._SafeText())
            organizer.log.addHandler(handler)
            organizer.log._app_file_handler = handler
            organizer.log._app_file_handler_dir = self.data_dir
            if organizer.log.level in (logging.NOTSET, logging.WARNING):
                organizer.log.setLevel(logging.INFO)
        except OSError:
            pass

    def _write_config(self, cfg):
        tmp = self.config_path.with_suffix(".tmp")
        tmp.write_text(json.dumps(cfg, indent=2, ensure_ascii=False), encoding="utf-8")
        os.replace(tmp, self.config_path)

    def _backup_config(self):
        if not self.config_path.exists():
            return
        folder = self.data_dir / "history" / "backups"
        folder.mkdir(parents=True, exist_ok=True)
        shutil.copy2(self.config_path, folder / f"organizer_config-{datetime.now():{DAY_FORMAT}}.json")
        for old in sorted(folder.glob("organizer_config-*.json"))[:-20]:
            old.unlink()

    # ------------------------------------------------------------------ settings file
    def load_config(self):
        self._use()
        cfg = copy.deepcopy(organizer.DEFAULT_CONFIG)
        try:
            user = json.loads(self.config_path.read_text(encoding="utf-8-sig"))
        except (OSError, ValueError) as exc:
            raise BackendError(f"Your settings file is damaged ({exc}). Open Settings and press "
                               f"'Reset to Standard' to start fresh (a backup is kept).", "damaged")
        if not isinstance(user, dict):
            raise BackendError("Your settings file is damaged. Press 'Reset to Standard' in Settings.", "damaged")
        cfg.update(user)
        organizer._fix_extension_dots(cfg)
        return cfg

    def save_config(self, cfg):
        probe = copy.deepcopy(cfg)
        probe["source"] = "."
        try:
            organizer.validate_config(probe)
        except SystemExit as exc:
            raise BackendError(str(exc.code))
        self._backup_config()
        self._write_config(cfg)

    def reset_damaged(self):
        self._backup_config()
        self._write_config(self.build_preset_config("standard"))

    def app_settings(self):
        base = {"auto_enabled": False, "auto_minutes": 30, "last_folder": "", "first_run_done": False,
                "tray_hint_shown": False}
        try:
            base.update(json.loads(self.settings_path.read_text(encoding="utf-8")))
        except (OSError, ValueError):
            pass
        return base

    def set_app_settings(self, **changes):
        current = self.app_settings()
        current.update(changes)
        self.settings_path.write_text(json.dumps(current, indent=2), encoding="utf-8")

    # ------------------------------------------------------------------ presets (ways of organizing)
    def list_presets(self):
        out = []
        for path in sorted(PRESET_DIR.glob("*.json")):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                out.append({"key": path.stem, "name": data["name"], "description": data["description"]})
            except (OSError, ValueError, KeyError):
                continue
        order = ["standard", "by_year", "student", "office", "photographer", "embedded", "minimal"]
        out.sort(key=lambda p: (order.index(p["key"]) if p["key"] in order else len(order), p["name"]))
        return out

    def build_preset_config(self, key):
        path = PRESET_DIR / f"{key}.json"
        try:
            preset = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            raise BackendError(f"Unknown way of organizing: {key}")
        cfg = copy.deepcopy(organizer.DEFAULT_CONFIG)
        cfg["topics"] = {}
        cfg.update(copy.deepcopy(preset.get("config", {})))
        if "rules_replace" in preset:
            cfg["rules"] = copy.deepcopy(preset["rules_replace"])
        for name, modes in preset.get("set_subfolders", {}).items():
            for rule in cfg["rules"]:
                if rule["name"] == name:
                    rule["subfolders"] = list(modes)
        cfg["_preset"] = key
        cfg["_customized"] = False
        return cfg

    def apply_preset(self, key):
        """Switch to a ready-made way of organizing; your watched folders and own ignore list are kept."""
        current = self.load_config() if self.config_path.exists() else organizer.DEFAULT_CONFIG
        new = self.build_preset_config(key)
        new["watch"] = list(current.get("watch", []))
        extras = [p for p in current.get("ignore_patterns", []) if p not in organizer.DEFAULT_CONFIG["ignore_patterns"]]
        new["ignore_patterns"] = list(organizer.DEFAULT_CONFIG["ignore_patterns"]) + extras
        self.save_config(new)

    def current_preset(self):
        cfg = self.load_config()
        key = cfg.get("_preset", "standard")
        names = {p["key"]: p["name"] for p in self.list_presets()}
        return names.get(key, key), bool(cfg.get("_customized"))

    def reset_to_standard(self):
        self.apply_preset("standard")

    # ------------------------------------------------------------------ my rules
    def _mark_custom(self, cfg):
        cfg["_customized"] = True

    def rule_rows(self):
        rows = []
        for i, rule in enumerate(self.load_config()["rules"]):
            what = ", ".join(rule.get("extensions", []) + rule.get("patterns", []))
            if "regex" in rule:
                what = (what + ", " if what else "") + "regex: " + rule["regex"]
            for key, label in (("min_size_mb", "from"), ("max_size_mb", "up to")):
                if key in rule:
                    what += f"  [{label} {rule[key]} MB]"
            modes = rule.get("subfolders", [])
            rows.append({"index": i, "name": rule["name"], "what": what, "dest": rule["dest"],
                         "subfolders": ", ".join(modes) if isinstance(modes, list) else str(modes),
                         "enabled": rule.get("enabled", True) is not False})
        return rows

    def get_rule(self, index):
        return copy.deepcopy(self.load_config()["rules"][index])

    @staticmethod
    def clean_rule(rule):
        """Check a rule typed in the editor and return the tidy version, or explain what is wrong."""
        name = str(rule.get("name", "")).strip()
        if not name:
            raise BackendError("Give the rule a name.")
        out = {"name": name}
        exts = [e.strip().lower() for e in (rule.get("extensions") or []) if e.strip()]
        out_exts = [e if e.startswith(".") else "." + e for e in exts]
        if out_exts:
            out["extensions"] = out_exts
        pats = [p.strip() for p in (rule.get("patterns") or []) if p.strip()]
        if pats:
            out["patterns"] = pats
        rx = str(rule.get("regex") or "").strip()
        if rx:
            try:
                re.compile(rx)
            except re.error as exc:
                raise BackendError(f"The pattern (regex) is not valid: {exc}")
            if organizer.regex_looks_slow(rx):
                raise BackendError("That pattern (regex) repeats inside repeats and could freeze the program. Simplify it.")
            out["regex"] = rx
        for key in ("min_size_mb", "max_size_mb"):
            if rule.get(key) not in (None, ""):
                try:
                    out[key] = float(rule[key])
                except (TypeError, ValueError):
                    raise BackendError("Sizes must be numbers (in MB).")
        if not any(k in out for k in ("extensions", "patterns", "regex", "min_size_mb", "max_size_mb")):
            raise BackendError("Say which files the rule is for: extensions, name patterns, a pattern or a size.")
        raw = str(rule.get("dest", "")).strip()
        if raw.startswith(("/", "\\", "~")):
            raise BackendError("The folder must be inside the folder being organized (for example  Projects/Work).")
        dest = raw.replace("\\", "/").strip("/")
        if not dest:
            raise BackendError("Say which folder the files go to.")
        norm = os.path.normpath(dest)
        if Path(dest).is_absolute() or re.match(r"^[A-Za-z]:", dest) or norm.startswith("..") or ".." in Path(norm).parts:
            raise BackendError("The folder must be inside the folder being organized (for example  Projects/Work).")
        out["dest"] = dest
        modes = [m for m in (rule.get("subfolders") or []) if m]
        bad = [m for m in modes if m not in organizer.SUBFOLDER_MODES]
        if bad:
            raise BackendError("Unknown sub-folder type: " + ", ".join(bad))
        if modes:
            out["subfolders"] = modes
        if rule.get("enabled") is False:
            out["enabled"] = False
        return out

    def add_rule(self, rule, at_top=True):
        cleaned = self.clean_rule(rule)
        cleaned["custom"] = True
        cfg = self.load_config()
        cfg["rules"].insert(0 if at_top else len(cfg["rules"]), cleaned)
        self._mark_custom(cfg)
        self.save_config(cfg)

    def update_rule(self, index, rule):
        cleaned = self.clean_rule(rule)
        cfg = self.load_config()
        old = cfg["rules"][index]
        for keep in ("custom", "sub_rules", "sub_default"):
            if keep in old:
                cleaned[keep] = old[keep]
        cfg["rules"][index] = cleaned
        self._mark_custom(cfg)
        self.save_config(cfg)

    def delete_rule(self, index):
        cfg = self.load_config()
        del cfg["rules"][index]
        self._mark_custom(cfg)
        self.save_config(cfg)

    def move_rule(self, index, delta):
        cfg = self.load_config()
        new = index + delta
        if 0 <= new < len(cfg["rules"]):
            cfg["rules"][index], cfg["rules"][new] = cfg["rules"][new], cfg["rules"][index]
            self._mark_custom(cfg)
            self.save_config(cfg)
        return max(0, min(new, len(cfg["rules"]) - 1))

    def set_rule_enabled(self, index, enabled):
        cfg = self.load_config()
        if enabled:
            cfg["rules"][index].pop("enabled", None)
        else:
            cfg["rules"][index]["enabled"] = False
        self._mark_custom(cfg)
        self.save_config(cfg)

    def where_would_go(self, filename, size_mb=0.0):
        """Where would a file with this name go? (a pretend file; nothing is touched)"""
        name = Path(str(filename).replace("\\", "/")).name.strip()
        if not name:
            raise BackendError("Type a file name, for example  holiday photo.jpg")
        cfg = self.load_config()
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp).resolve()
            probe = base / name
            probe.write_bytes(b"")
            dest, label = organizer.pick_destination(cfg, base, probe, int(size_mb * 1024 * 1024))
            if dest is None:
                return None, "stays where it is"
            return str(Path(dest).relative_to(base)).replace("\\", "/"), label

    # ------------------------------------------------------------------ topics, ignore list, watched folders, options
    def get_topics(self):
        return copy.deepcopy(self.load_config().get("topics", {}))

    def set_topics(self, topics):
        clean = {}
        for name, words in topics.items():
            name = str(name).strip()
            words = [w.strip().lower() for w in words if w.strip()]
            if name and words:
                clean[name] = words
        cfg = self.load_config()
        cfg["topics"] = clean
        self._mark_custom(cfg)
        self.save_config(cfg)

    def get_ignore(self):
        return list(self.load_config().get("ignore_patterns", []))

    def set_ignore(self, patterns):
        cfg = self.load_config()
        cfg["ignore_patterns"] = [p.strip() for p in patterns if p.strip()]
        self.save_config(cfg)

    def get_watch(self):
        return [w if isinstance(w, str) else w.get("path", "") for w in self.load_config().get("watch", [])]

    def add_watch(self, path):
        path = str(Path(path).expanduser())
        if not Path(path).is_dir():
            raise BackendError(f"That folder does not exist: {path}")
        cfg = self.load_config()
        if path not in self.get_watch():
            cfg.setdefault("watch", []).append(path)
            self.save_config(cfg)

    def remove_watch(self, path):
        cfg = self.load_config()
        cfg["watch"] = [w for w in cfg.get("watch", []) if (w if isinstance(w, str) else w.get("path")) != path]
        self.save_config(cfg)

    OPTION_KEYS = ("on_conflict", "min_age_seconds", "recursive", "dedupe_identical", "ignore_hidden")

    def get_options(self):
        cfg = self.load_config()
        return {k: cfg.get(k) for k in self.OPTION_KEYS}

    def set_options(self, **options):
        cfg = self.load_config()
        for key, value in options.items():
            if key not in self.OPTION_KEYS:
                raise BackendError(f"Unknown option: {key}")
            cfg[key] = value
        self.save_config(cfg)

    # ------------------------------------------------------------------ organizing
    def _prepare(self, folder, include_new, recursive, force):
        self._use()
        base = Path(folder).expanduser()
        if not str(folder).strip() or not base.is_dir():
            raise BackendError(f"Choose a folder that exists. ({folder})")
        base = base.resolve()
        cfg = self.load_config()
        cfg["source"] = str(base)
        if include_new:
            cfg["min_age_seconds"] = 0
        if recursive is not None:
            cfg["recursive"] = bool(recursive)
        try:
            organizer.validate_config(cfg)
            organizer.check_safe(base, cfg["recursive"], force)
        except SystemExit as exc:
            raise BackendError(str(exc.code), "unsafe" if "Stopped" in str(exc.code) or "Refusing" in str(exc.code) else "error")
        return cfg, base

    def run(self, folder, dry_run=True, include_new=False, recursive=None, force=False, scheduled=False):
        """Preview (dry_run=True) or really organize one folder. Returns what happened."""
        cfg, base = self._prepare(folder, include_new, recursive, force)
        result = {"folder": str(base), "dry_run": dry_run, "plan": [], "stats": {}, "lines": [], "status": "ok"}
        mode = "scheduled" if scheduled else "manual"
        with _capturing() as (cap, out):
            pause = None if dry_run else organizer.get_pause()
            if pause and scheduled:
                result["status"] = "paused"
                organizer.record_run(base, {}, mode, "paused")
            else:
                guard = contextlib.nullcontext(True) if dry_run else organizer.run_lock(base)
                with guard as free:
                    if not free:
                        result["status"] = "busy"
                        organizer.record_run(base, {}, mode, "busy")
                    else:
                        try:
                            stats = organizer.organize(cfg, base, dry_run)
                        except Exception:
                            if not dry_run:
                                organizer.record_run(base, {}, mode, "error")
                            raise
                        result["stats"] = stats
                        if not dry_run:
                            organizer.record_run(base, stats, mode, "stopped" if stats.get("aborted") else "ok")
                            organizer.maybe_auto_archive(cfg, base, False)
        result["lines"] = list(cap.lines)
        for line in cap.lines:
            m = PLAN_LINE.match(line)
            if m and not line.startswith(("summary", "done", "tip")):
                result["plan"].append({"name": m.group(1), "dest": m.group(2), "rule": m.group(3)})
        return result

    def run_all(self, dry_run=False, scheduled=False):
        out = []
        for folder in self.get_watch():
            try:
                out.append((folder, self.run(folder, dry_run=dry_run, scheduled=scheduled)))
            except BackendError as exc:
                out.append((folder, {"status": "error", "error": str(exc), "stats": {}, "plan": [], "lines": []}))
        return out

    # ------------------------------------------------------------------ history and undo
    def _base(self, folder):
        self._use()
        base = Path(folder).expanduser()
        if not base.is_dir():
            raise BackendError(f"Choose a folder that exists. ({folder})")
        return base.resolve()

    def history(self, folder):
        _, entries = organizer.read_history(self._base(folder))
        runs = {}
        for e in entries:
            runs.setdefault(e["run"], []).append(e)
        out = []
        for run_id, items in runs.items():
            out.append({"run": run_id, "time": items[0].get("time", "?").replace("T", " ")[:16], "count": len(items),
                        "examples": ", ".join(Path(i["dst"]).name for i in items[:3])})
        return list(reversed(out))

    def history_items(self, folder, run_id):
        _, entries = organizer.read_history(self._base(folder))
        return [{"name": Path(e["dst"]).name, "from": str(Path(e["src"]).parent), "to": str(Path(e["dst"]).parent)}
                for e in entries if e["run"] == run_id]

    def undo(self, folder, run_id=None):
        base = self._base(folder)
        with _capturing() as (cap, _out):
            organizer.undo_run(base, dry_run=False, run_id=run_id)
        return cap.lines

    def restore(self, folder, names):
        base = self._base(folder)
        with _capturing() as (cap, _out):
            organizer.restore_files(base, list(names), dry_run=False)
        return cap.lines

    # ------------------------------------------------------------------ dashboard
    def health_text(self):
        self._use()
        with _capturing() as (_cap, out):
            code = organizer.run_doctor(self.load_config(), full=True)
        return out.getvalue(), code

    def space_text(self, folder):
        base = self._base(folder)
        with _capturing() as (_cap, out):
            organizer.space_report(self.load_config(), base)
        return out.getvalue()

    def duplicates_text(self, folder):
        base = self._base(folder)
        with _capturing() as (cap, out):
            organizer.find_duplicates(self.load_config(), base, set_aside=False, dry_run=False, assume_yes=True)
        return out.getvalue() + "\n".join(cap.lines)

    def set_aside_duplicates(self, folder):
        base = self._base(folder)
        with _capturing() as (cap, out):
            organizer.find_duplicates(self.load_config(), base, set_aside=True, dry_run=False, assume_yes=True)
        return out.getvalue() + "\n".join(cap.lines)

    def recent_runs(self, limit=15):
        self._use()
        return list(reversed(organizer.read_ledger()))[:limit]

    def pause_status(self):
        self._use()
        pause = organizer.get_pause()
        return None if not pause else organizer.describe_pause(pause)

    def snooze(self, text):
        self._use()
        with _capturing() as (_cap, out):
            try:
                organizer.do_snooze(text)
            except SystemExit as exc:
                raise BackendError(str(exc.code))
        return out.getvalue().strip()

    def resume(self):
        self._use()
        with _capturing() as (_cap, out):
            organizer.do_resume()
        return out.getvalue().strip()

    # ------------------------------------------------------------------ share settings between people / PCs
    def export_settings(self, path):
        cfg = self.load_config()
        for key in ("watch", "source"):
            cfg.pop(key, None)
        Path(path).write_text(json.dumps(cfg, indent=2, ensure_ascii=False), encoding="utf-8")

    def import_settings(self, path):
        try:
            data = json.loads(Path(path).read_text(encoding="utf-8-sig"))
        except (OSError, ValueError) as exc:
            raise BackendError(f"That file could not be read as Organizer settings ({exc}).")
        if not isinstance(data, dict) or not isinstance(data.get("rules"), list):
            raise BackendError("That file does not look like Organizer settings (no rules found).")
        current = self.load_config()
        new = copy.deepcopy(organizer.DEFAULT_CONFIG)
        new.update(data)
        new["watch"] = list(current.get("watch", []))
        new.pop("source", None)
        new["_customized"] = True
        self.save_config(new)

    # ------------------------------------------------------------------ start with Windows
    @staticmethod
    def startup_dir():
        if not sys.platform.startswith("win"):
            return None
        return Path(os.environ.get("APPDATA", "")) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"

    def _startup_file(self, startup_dir=None):
        folder = Path(startup_dir) if startup_dir else self.startup_dir()
        return folder / "Organizer Tray.vbs" if folder else None

    def startup_enabled(self, startup_dir=None):
        f = self._startup_file(startup_dir)
        return bool(f and f.exists())

    def set_startup(self, enabled, startup_dir=None):
        f = self._startup_file(startup_dir)
        if f is None:
            raise BackendError("Starting with Windows only works on Windows.")
        if not enabled:
            f.unlink(missing_ok=True)
            return
        if getattr(sys, "frozen", False):
            command = f'"{sys.executable}" --tray'
        else:
            pyw = Path(sys.executable).with_name("pythonw.exe")
            exe = pyw if pyw.exists() else Path(sys.executable)
            command = f'"{exe}" "{APP_DIR / "organizer_app.py"}" --tray'
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text('Set sh = CreateObject("WScript.Shell")\r\nsh.Run "' + command.replace('"', '""') + '", 0, False\r\n',
                     encoding="utf-8")
