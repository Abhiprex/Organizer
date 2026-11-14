#!/usr/bin/env python3
"""
Organizer 2.8 - repair tool  (double-click repair.bat)

Looks for everything that commonly goes wrong and fixes what it safely can. Whatever it
changes is backed up first (history\\backups), and it never touches your organized files.

  python repair.py              menu (easiest)
  python repair.py --check      only look, change nothing
  python repair.py --fix        look, then fix (asks once; --yes skips the questions)
  python repair.py --report     write Organizer-report.txt (to send when asking for help)

What it can repair
  * a damaged / unreadable settings file  -> keeps what is still good, else restores a backup
  * settings with a wrong value           -> only the wrong parts are reset, the rest is kept
  * the automatic task: missing, switched off, pointing at another copy, Python moved
  * the right-click menu pointing at another copy
  * stale locks, damaged history lines, a half-written settings file, a leftover pause
  * a missing history folder
What it can only tell you about (it cannot create missing program files)
  * missing, damaged or mixed-version program files -> unzip the newest zip over this folder
  * watched folders that are missing, folders Organizer may not write to, a too-old Python
"""

import argparse
import contextlib
import copy
import io
import json
import os
import platform
import re
import shutil
import sys
import time
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))


def data_dir():
    """Same rule as organizer.default_data_dir() (kept separate so repair works even if organizer.py is damaged)."""
    override = os.environ.get("ORGANIZER_HOME")
    if override:
        return Path(override)
    if os.environ.get("ORGANIZER_PORTABLE") or (HERE / "portable.txt").exists():
        return HERE
    if sys.platform.startswith("win"):
        return Path(os.environ.get("APPDATA") or Path.home()) / "Organizer"
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "Organizer"
    return Path(os.environ.get("XDG_DATA_HOME") or Path.home() / ".local" / "share") / "organizer"


_USER_CONFIG = data_dir() / "organizer_config.json"
CONFIG = _USER_CONFIG if _USER_CONFIG.exists() else HERE / "organizer_config.json"
HISTORY = data_dir() / "history"
BACKUPS = HISTORY / "backups"
PY_FILES = ["organizer.py", "manage_folders.py", "setup_windows.py", "repair.py", "app_backend.py", "app_window.py", "organizer_app.py"]
BAT_FILES = ["install.bat", "uninstall.bat", "folders.bat", "doctor.bat", "snooze.bat", "resume.bat",
             "space.bat", "repair.bat", "app.bat", "selftest.bat", "build_exe.bat"]
UNZIP_HINT = ("unzip the newest Organizer zip over this folder "
              "(keep your organizer_config.json and the history folder)")


# --------------------------------------------------------------------------- #
# Small helpers
# --------------------------------------------------------------------------- #
def stamp():
    return datetime.now().strftime("%Y%m%d-%H%M%S")


def ask(question, default_yes=True):
    """Yes/no question. No answer is possible when nobody is there (non-interactive) -> default."""
    if sys.stdin is None or not sys.stdin.isatty():
        return False
    answer = input(f"{question} [{'Y/n' if default_yes else 'y/N'}] ").strip().lower()
    return default_yes if not answer else answer in ("y", "yes")


def decode_text(raw):
    """File bytes -> text. Handles UTF-8, Notepad's UTF-8 BOM and PowerShell's UTF-16."""
    try:
        return raw.decode("utf-8-sig"), "utf-8"
    except UnicodeDecodeError:
        return raw.decode("utf-16"), "utf-16"


def backup_copy(path, label):
    """Copy a file into history\\backups (or next to it if that is not possible)."""
    path = Path(path)
    if not path.exists():
        return None
    for folder in (BACKUPS, path.parent):
        try:
            folder.mkdir(parents=True, exist_ok=True)
            target = folder / f"{path.stem}-{label}-{stamp()}{path.suffix}"
            shutil.copyfile(path, target)            # content only: the backup's own time is 'now'
            return target
        except OSError:
            continue
    return None


def write_json(path, data):
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.replace(path)                                      # never leaves a half-written file


def redact(text):
    """Hide the user name in anything that will be sent to someone else."""
    for value in {str(Path.home()), os.environ.get("USERPROFILE", ""), os.path.expanduser("~")}:
        if value and len(value) > 3:
            text = text.replace(value, "~")
    for var in ("USERNAME", "USER"):
        name = os.environ.get(var, "")
        if len(name) >= 3:
            text = re.sub(re.escape(name), "<user>", text, flags=re.IGNORECASE)
    return text


class Finding:
    """One thing that is not right.  fix = what to run; manual = what only the user can do."""

    def __init__(self, title, level="problem", fix=None, how="", question=None, destructive=False,
                 manual=None, deliberate=False):
        self.title, self.level, self.fix, self.how = title, level, fix, how
        self.question, self.destructive, self.manual = question, destructive, manual
        self.deliberate = deliberate        # something you chose (a pause): only an explicit "yes" changes it


def import_organizer():
    try:
        import organizer
        return organizer, None
    except Exception as exc:                               # a damaged organizer.py must not stop the repair tool
        return None, exc


# --------------------------------------------------------------------------- #
# Checks: program files
# --------------------------------------------------------------------------- #
def check_files(findings):
    versions = {}
    for name in PY_FILES:
        path = HERE / name
        if not path.exists():
            findings.append(Finding(f"{name} is missing", manual=UNZIP_HINT))
            continue
        try:
            text = path.read_bytes().decode("utf-8-sig")
            compile(text, name, "exec")
        except (SyntaxError, ValueError, UnicodeDecodeError) as exc:
            findings.append(Finding(f"{name} is damaged ({type(exc).__name__}: {exc})", manual=UNZIP_HINT))
            continue
        found = re.search(r"Organizer (\d+(?:\.\d+)+)", text[:600])
        if found:
            versions[name] = found.group(1)
    if len(set(versions.values())) > 1:
        detail = ", ".join(f"{n} {v}" for n, v in versions.items())
        findings.append(Finding(f"program files from different versions are mixed together ({detail})",
                                manual=UNZIP_HINT))
    missing = [name for name in BAT_FILES if not (HERE / name).exists()]
    if missing:
        findings.append(Finding("these helper files are missing: " + ", ".join(missing),
                                level="warning", manual=UNZIP_HINT))
    if sys.version_info < (3, 8):
        findings.append(Finding(f"Python {sys.version_info.major}.{sys.version_info.minor} is too old (3.8+ needed)",
                                manual="install a newer Python from python.org, then run install.bat again"))
    return versions


def check_writable(findings):
    for folder in (HERE, HISTORY):
        if not folder.exists():
            continue                                       # a missing history folder is reported (and fixed) elsewhere
        try:
            probe = folder / f".write_test_{os.getpid()}"
            probe.write_text("ok")
            probe.unlink()
        except OSError as exc:
            findings.append(Finding(f"Organizer is not allowed to write in {folder} ({exc})",
                                    manual="move the Organizer folder somewhere you own (for example D:\\Organizer "
                                           "or your Documents) - not Program Files, a read-only drive or a "
                                           "folder your antivirus protects"))


# --------------------------------------------------------------------------- #
# Checks: settings file
# --------------------------------------------------------------------------- #
def read_config_data():
    """(data, encoding, problem). data is None when the file is missing or unreadable."""
    if not CONFIG.exists():
        return None, None, "missing"
    try:
        text, encoding = decode_text(CONFIG.read_bytes())
    except (OSError, UnicodeDecodeError) as exc:
        return None, None, f"unreadable ({exc})"
    try:
        data = json.loads(text)
    except ValueError as exc:
        return None, encoding, f"not valid JSON ({exc})"
    if not isinstance(data, dict):
        return None, encoding, "it must contain a JSON object { ... }"
    return data, encoding, None


def validate(org, data):
    """None if the settings are usable, else the plain-language reason."""
    merged = copy.deepcopy(org.DEFAULT_CONFIG)
    merged.update(data)
    try:
        org.validate_config(merged)
    except SystemExit as exc:
        return str(exc.code)
    except Exception as exc:
        return f"unexpected value ({type(exc).__name__}: {exc})"
    return None


def salvage(org, data):
    """Keep everything that is fine; reset only the parts that are wrong. Returns (fixed, notes)."""
    fixed, notes = copy.deepcopy(data), []

    def reset(key, why):
        fixed.pop(key, None)
        notes.append(f'reset "{key}" to its default ({why})')

    kinds = {"watch": list, "topics": dict, "folders": dict, "cleanup": dict, "unknown_extensions": dict, "rules": list, "subfolders": list,
             "ignore_patterns": list, "partial_extensions": list, "recursive": bool, "ignore_hidden": bool,
             "dedupe_identical": bool}
    for key, kind in kinds.items():
        if key in fixed and not isinstance(fixed[key], kind):
            reset(key, f"expected {kind.__name__}")
    minutes = fixed.get("schedule_minutes")
    if "schedule_minutes" in fixed and (not isinstance(minutes, int) or isinstance(minutes, bool)
                                        or not 1 <= minutes <= 1440):
        reset("schedule_minutes", "must be 1-1440")
    if "on_conflict" in fixed and fixed["on_conflict"] not in ("rename", "skip", "overwrite"):
        reset("on_conflict", "must be rename, skip or overwrite")
    for key in ("min_age_seconds",):
        if key in fixed and (not isinstance(fixed[key], (int, float)) or isinstance(fixed[key], bool)):
            reset(key, "must be a number")

    def good_rule(rule):
        if not isinstance(rule, dict) or "name" not in rule or "dest" not in rule:
            return False
        for key in ("extensions", "patterns"):
            if key in rule and not isinstance(rule[key], list):
                return False
        if "regex" in rule:
            try:
                re.compile(rule["regex"])
            except (re.error, TypeError):
                return False
        return True

    if isinstance(fixed.get("rules"), list):
        kept = [r for r in fixed["rules"] if good_rule(r)]
        if len(kept) != len(fixed["rules"]):
            notes.append(f'dropped {len(fixed["rules"]) - len(kept)} folder rule(s) that were incomplete')
        fixed["rules"] = kept
    if isinstance(fixed.get("watch"), list):
        kept = [w for w in fixed["watch"] if isinstance(w, str) or (isinstance(w, dict) and w.get("path"))]
        if len(kept) != len(fixed["watch"]):
            notes.append(f'dropped {len(fixed["watch"]) - len(kept)} unusable watched-folder entry(ies)')
        fixed["watch"] = kept
    for block, rules_key in (("folders", "rules"), ("cleanup", "rules")):
        inner = fixed.get(block)
        if isinstance(inner, dict) and isinstance(inner.get(rules_key), list):
            needed = ("name", "dest") if block == "folders" else ("name", "folder_rule", "older_than_days")
            kept = [r for r in inner[rules_key] if isinstance(r, dict) and all(k in r for k in needed)]
            if len(kept) != len(inner[rules_key]):
                notes.append(f'dropped {len(inner[rules_key]) - len(kept)} incomplete rule(s) in "{block}"')
            inner[rules_key] = kept
    for _ in range(4):                                     # anything still wrong: reset the key the message names
        problem = validate(org, fixed)
        if problem is None:
            return fixed, notes
        named = [k for k in re.findall(r'"([a-z_]+)"', problem) if k in fixed]
        if not named:
            return None, notes
        reset(named[0], "it was not valid")
    return None, notes


def backup_sort_key(path):
    """When a backup was made: the stamp in its name (YYYYmmdd-HHMMSS), else the file time."""
    found = re.search(r"(\d{8}-\d{6})", path.name)
    if found:
        return found.group(1)
    return datetime.fromtimestamp(path.stat().st_mtime).strftime("%Y%m%d-%H%M%S")


def backup_candidates():
    found = []
    bak = CONFIG.with_name(CONFIG.name + ".bak")
    if bak.exists():
        found.append(("the settings as they were before your last change in folders.bat", bak))
    if BACKUPS.exists():
        files = sorted(BACKUPS.glob("organizer_config-*.json"), key=backup_sort_key, reverse=True)
        found += [(f"backup {p.name}", p) for p in files]
    return found


def load_json_file(path):
    try:
        text, _ = decode_text(Path(path).read_bytes())
        data = json.loads(text)
        return data if isinstance(data, dict) else None
    except (OSError, ValueError):
        return None


def default_settings(org, keep_from=None):
    fresh = copy.deepcopy(org.DEFAULT_CONFIG)
    if isinstance(keep_from, dict):
        if isinstance(keep_from.get("watch"), list):
            fresh["watch"] = [w for w in keep_from["watch"] if isinstance(w, str) or (isinstance(w, dict) and w.get("path"))]
        minutes = keep_from.get("schedule_minutes")
        if isinstance(minutes, int) and not isinstance(minutes, bool) and 1 <= minutes <= 1440:
            fresh["schedule_minutes"] = minutes
    return fresh


def repair_settings(org):
    """Make organizer_config.json usable again. Returns what was done."""
    data, encoding, problem = read_config_data()
    saved = backup_copy(CONFIG, "before-repair") if CONFIG.exists() else None
    note = f" (your previous file is saved as {saved.name})" if saved else ""
    if data is not None:
        fixed, notes = salvage(org, data)
        if fixed is not None:
            write_json(CONFIG, fixed)
            return "kept your settings and " + "; ".join(notes or ["rewrote the file cleanly"]) + note
    for label, path in backup_candidates():
        candidate = load_json_file(path)
        if candidate is not None and validate(org, candidate) is None:
            write_json(CONFIG, candidate)
            return f"restored {label}{note}"
    write_json(CONFIG, default_settings(org, data))
    if data is not None:
        kept = " (your watched folders and run interval were kept)"
    elif problem == "missing":
        kept = " (there was no settings file; add your watched folders in folders.bat, option 8)"
    else:
        kept = " (the old file could not be read, so add your watched folders again: folders.bat, option 8)"
    return "no usable backup was found, so fresh default settings were written" + kept + note


def check_settings(org, findings):
    """Returns the merged config when the settings are fine, else None."""
    data, encoding, problem = read_config_data()
    if problem == "missing":
        findings.append(Finding("the settings file organizer_config.json is missing (built-in defaults are used)",
                                level="warning", fix=lambda: repair_settings(org),
                                how="create a fresh settings file with the default folders"))
        return None
    if data is None:
        findings.append(Finding(f"the settings file is damaged: {problem}", fix=lambda: repair_settings(org),
                                how="keep what is readable, else restore your newest good backup, else defaults"))
        return None
    reason = validate(org, data)
    if reason:
        findings.append(Finding(f"the settings file has a mistake: {reason}", fix=lambda: repair_settings(org),
                                how="reset only the wrong parts and keep the rest (a backup is saved first)"))
        return None
    if encoding == "utf-16":
        findings.append(Finding("the settings file is saved as UTF-16 (some tools do this)", level="warning",
                                fix=lambda: repair_settings(org), how="re-save it as normal UTF-8, content unchanged"))
    merged, _ = org.load_config(str(CONFIG)) if encoding != "utf-16" else (None, None)
    if merged is None:
        merged = copy.deepcopy(org.DEFAULT_CONFIG)
        merged.update(data)
    return merged


# --------------------------------------------------------------------------- #
# Checks: history folder, pause, scheduled task, right-click menu, watched folders
# --------------------------------------------------------------------------- #
def jsonl_damage(path):
    bad, good = 0, []
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                if isinstance(json.loads(line), dict):
                    good.append(line)
                    continue
            except ValueError:
                pass
            bad += 1
    except (OSError, UnicodeDecodeError):
        return 0, []
    return bad, good


def fix_jsonl(path):
    bad, good = jsonl_damage(path)
    saved = backup_copy(path, "before-repair")
    path.write_text("".join(line + "\n" for line in good), encoding="utf-8")
    return f"removed {bad} damaged line(s) from {path.name}" + (f" (original saved as {saved.name})" if saved else "")


def check_history(org, findings):
    if not HISTORY.exists():
        findings.append(Finding("the history folder is missing", level="warning",
                                fix=lambda: (HISTORY.mkdir(parents=True, exist_ok=True) or "created the history folder"),
                                how="create it (undo history starts empty)"))
        return
    locks = []
    for lock in HISTORY.glob("*.lock"):
        try:
            if time.time() - lock.stat().st_mtime > 900:
                locks.append(lock)
        except OSError:
            pass
    if locks:
        def clear_locks():
            for lock in locks:
                lock.unlink(missing_ok=True)
            return f"removed {len(locks)} stale lock file(s)"
        findings.append(Finding(f"{len(locks)} stale lock file(s) from a crashed run block that folder",
                                level="warning", fix=clear_locks, how="delete them (they are only markers)"))
    for path in sorted(HISTORY.glob("*.jsonl")):
        bad, _ = jsonl_damage(path)
        if bad:
            findings.append(Finding(f"{path.name} has {bad} damaged line(s)", level="warning",
                                    fix=lambda p=path: fix_jsonl(p),
                                    how="remove only the damaged lines (a copy of the original is kept)"))
    pause = HISTORY / "paused.json"
    if pause.exists():
        try:
            json.loads(pause.read_text(encoding="utf-8"))["until"]
        except (OSError, ValueError, KeyError, TypeError):
            findings.append(Finding("the pause marker is damaged", level="warning",
                                    fix=lambda: (pause.unlink(missing_ok=True) or "removed the damaged pause marker"),
                                    how="delete it (automatic organizing runs normally again)"))
    for tmp in HERE.glob("*.tmp"):
        try:
            if time.time() - tmp.stat().st_mtime > 300:
                findings.append(Finding(f"{tmp.name} is a leftover from an interrupted save", level="warning",
                                        fix=lambda t=tmp: (t.unlink(missing_ok=True) or f"removed {t.name}"),
                                        how="delete it (your real settings file is not touched)"))
        except OSError:
            pass


def read_pause():
    """The pause state WITHOUT changing anything (org.get_pause() creates folders and deletes
    expired markers, which a read-only check must not do). None / 'forever' / datetime."""
    path = HISTORY / "paused.json"
    if not path.exists():
        return None
    try:
        until = json.loads(path.read_text(encoding="utf-8"))["until"]
        if until == "forever":
            return "forever"
        ends = datetime.fromisoformat(until)
    except (OSError, ValueError, KeyError, TypeError):
        return None
    return ends if ends > datetime.now() else None


def check_pause(org, findings):
    pause = read_pause()
    if pause:
        findings.append(Finding(f"automatic organizing is paused {org.describe_pause(pause)}", level="info",
                                question="Resume automatic organizing now?", deliberate=True,
                                fix=lambda: (org.clear_pause() and "automatic organizing is on again") or "was not paused",
                                how="remove the pause (only if you say yes: a pause is your choice)"))


def check_windows(org, cfg, findings):
    try:
        import setup_windows as sw
    except Exception as exc:
        findings.append(Finding(f"setup_windows.py cannot be loaded ({exc})", manual=UNZIP_HINT))
        return
    if not sw.is_windows():
        return
    minutes = cfg.get("schedule_minutes", 30)
    task = org.query_task()
    me = str(HERE / "organizer.py").lower()

    def recreate():
        ok, message = sw.create_task(minutes)
        if not ok:
            raise RuntimeError(message)
        return f"automatic task re-created, every {minutes} minutes ({message})"

    if task is None:
        pass
    elif task.get("error"):
        findings.append(Finding(f"could not talk to Task Scheduler ({task['error']})", level="warning",
                                manual="open Task Scheduler and look for the task 'FolderOrganizer'"))
    elif not task["installed"]:
        findings.append(Finding("the automatic task is not installed", level="warning",
                                question="Install automatic organizing now?", fix=recreate,
                                how=f"create the scheduled task (every {minutes} minutes)"))
    else:
        reasons = []
        if not task["enabled"]:
            reasons.append("it is switched off")
        if me not in task["arguments"].lower():
            reasons.append("it runs a different copy of Organizer")
        if task["command"] and not Path(task["command"]).exists():
            reasons.append("Python was not found where it expects")
        if "--all" not in task["arguments"]:
            reasons.append("it is from an older version")
        if reasons:
            findings.append(Finding("the automatic task needs repair: " + "; ".join(reasons), fix=recreate,
                                    how="re-create the task from this folder with the current Python"))
    menu = org.query_menu()
    if menu and menu["installed"] and not menu["here"]:
        findings.append(Finding("the right-click menu points at a different copy of Organizer", level="warning",
                                fix=lambda: (sw.add_menu() or "right-click menu re-created"),
                                how="re-create the right-click entries from this folder"))


def check_watched(org, cfg, findings):
    entries = org.watch_entries(cfg)
    if not entries:
        findings.append(Finding("no folders are watched, so automatic runs have nothing to do", level="info",
                                manual='add one in folders.bat (option 8) or install.bat'))
    for path, _ in entries:
        base = Path(path).expanduser()
        if not base.is_dir():
            def remove(p=path):
                config = json.loads(CONFIG.read_text(encoding="utf-8-sig"))
                before = len(config.get("watch", []))
                config["watch"] = [w for w in config.get("watch", [])
                                   if (w if isinstance(w, str) else w.get("path", "")).lower() != p.lower()]
                backup_copy(CONFIG, "before-repair")
                write_json(CONFIG, config)
                return f"removed {p} from the watched list ({before - len(config['watch'])} entry)"
            findings.append(Finding(f"watched folder not found: {base}", level="warning", destructive=True,
                                    question=f"Remove {base} from the watched list? (say No if it is a USB drive "
                                             "or network folder that is just not connected right now)",
                                    fix=remove, how="remove it from the list",
                                    manual="reconnect the drive, or fix the path in folders.bat (option 8)"))
        elif not os.access(base, os.W_OK):
            findings.append(Finding(f"Organizer is not allowed to change {base}", manual="check the folder's permissions"))


def diagnose():
    """Returns (findings, context)."""
    findings = []
    check_files(findings)
    check_writable(findings)
    org, error = import_organizer()
    context = {"org": org, "cfg": None}
    if org is None:
        findings.append(Finding(f"organizer.py cannot be loaded ({type(error).__name__}: {error})", manual=UNZIP_HINT))
        return findings, context
    cfg = check_settings(org, findings)
    context["cfg"] = cfg
    check_history(org, findings)
    if cfg is not None:
        check_pause(org, findings)
        check_windows(org, cfg, findings)
        check_watched(org, cfg, findings)
    return findings, context


# --------------------------------------------------------------------------- #
# Doing the repairs
# --------------------------------------------------------------------------- #
MARKS = {"problem": "[X] ", "warning": "[!] ", "info": "[..]"}


def show(findings):
    for finding in findings:
        print(f"  {MARKS[finding.level]} {finding.title}")
        if finding.fix and finding.how:
            print(f"          will: {finding.how}")
        if finding.manual and not finding.fix:
            print(f"          you: {finding.manual}")


def run_fixes(findings, assume_yes):
    """Runs the fixes. Returns [(finding, outcome text)]."""
    outcomes = []
    for finding in findings:
        if finding.fix is None:
            continue
        if finding.destructive or finding.deliberate:
            if assume_yes or not ask(finding.question, default_yes=not finding.destructive):
                outcomes.append((finding, "left as it is"))
                continue
        elif finding.question and not assume_yes and not ask(finding.question):
            outcomes.append((finding, "left as it is"))
            continue
        try:
            outcomes.append((finding, finding.fix()))
        except Exception as exc:
            outcomes.append((finding, f"FAILED: {exc}"))
    return outcomes


def cmd_fix(check_only=False, assume_yes=False):
    findings, context = diagnose()
    print(f"Organizer repair - {len(findings)} thing(s) found\n" if findings else "Organizer repair\n")
    if not findings:
        print("  [ok]  everything checked is fine")
        print("\nNothing to repair.")
        return 0
    show(findings)
    problems = sum(1 for f in findings if f.level == "problem")
    if check_only:
        print(f"\n{problems} problem(s). Nothing was changed (check only).")
        return 1 if problems else 0
    fixable = [f for f in findings if f.fix]
    if not fixable:
        print("\nNothing here can be fixed automatically - see the lines marked 'you:'.")
        return 1
    if not assume_yes and not ask(f"\nFix {len(fixable)} thing(s) now? (backups are kept in history\\backups)"):
        print("Nothing was changed.")
        return 1
    print()
    for finding, outcome in run_fixes(findings, assume_yes):
        print(f"  * {finding.title}\n      -> {outcome}")

    again, context = diagnose()
    left = [f for f in again if f.level != "info" or f.fix]
    print()
    if not left:
        print("All fixed. Everything checked is fine now.")
    else:
        print("Still needs your attention:")
        show(left)
    org, cfg = context["org"], context["cfg"]
    if org is not None and cfg is not None:
        print()
        with contextlib.suppress(Exception):
            org.run_doctor(cfg, full=False)
    return 1 if any(f.level == "problem" for f in again) else 0


# --------------------------------------------------------------------------- #
# Restore / reset / report
# --------------------------------------------------------------------------- #
def describe_settings(org, path):
    data = load_json_file(path)
    if data is None:
        return "damaged, cannot be used"
    if validate(org, data):
        return "has mistakes"
    return f"{len(data.get('rules', []))} folder rules, {len(data.get('watch', []))} watched folder(s)"


def cmd_restore(org):
    options = backup_candidates()
    if not options:
        print("There is no settings backup yet. (Backups are made whenever settings change.)")
        return 1
    print("Settings backups (newest first):")
    for number, (label, path) in enumerate(options, 1):
        key = backup_sort_key(path)
        when = f"{key[:4]}-{key[4:6]}-{key[6:8]} {key[9:11]}:{key[11:13]}"
        print(f"  {number}) {label}   [{when}]  - {describe_settings(org, path)}")
    choice = input("\nRestore which one? (number, Enter = cancel): ").strip()
    if not choice.isdigit() or not 1 <= int(choice) <= len(options):
        print("Nothing was changed.")
        return 0
    label, path = options[int(choice) - 1]
    chosen = load_json_file(path)
    if chosen is None or validate(org, chosen):
        print("That backup cannot be used (it is damaged or has mistakes). Nothing was changed.")
        return 1
    if not ask(f"Replace your current settings with {label}? (your current ones are saved first)"):
        print("Nothing was changed.")
        return 0
    saved = backup_copy(CONFIG, "replaced")
    write_json(CONFIG, chosen)
    print("Restored." + (f" Your previous settings are saved as {saved.name}." if saved else ""))
    return 0


def cmd_reset(org):
    print("This puts the built-in default settings back: the default folders and topics.")
    print("Your own folders / topics / rules are removed (a backup is kept, so nothing is lost for good).")
    if not ask("Continue?", default_yes=False):
        print("Nothing was changed.")
        return 0
    current = load_json_file(CONFIG)
    keep = bool(current) and ask("Keep your watched folders and how-often setting?")
    saved = backup_copy(CONFIG, "before-reset")
    write_json(CONFIG, default_settings(org, current if keep else None))
    print("Settings reset." + (f" Your previous settings are saved as {saved.name} (menu option 3 restores it)." if saved else ""))
    return 0


def build_report():
    org, error = import_organizer()
    out = io.StringIO()
    p = lambda *a: print(*a, file=out)
    p(f"Organizer support report - {datetime.now():%Y-%m-%d %H:%M}")
    p(f"Python {platform.python_version()} on {platform.platform()}")
    p(f"Folder: {HERE}")
    p("\n== Program files ==")
    versions = {}
    for name in PY_FILES + BAT_FILES + ["organizer_config.json", "README.txt"]:
        path = HERE / name
        if path.exists():
            version = ""
            if name.endswith(".py"):
                found = re.search(r"Organizer (\d+(?:\.\d+)+)", path.read_text(encoding="utf-8", errors="replace")[:600])
                version = f"  version {found.group(1)}" if found else ""
            p(f"  {name:<24} {path.stat().st_size:>8} bytes{version}")
        else:
            p(f"  {name:<24} MISSING")
    p("\n== Findings of the repair check ==")
    findings, context = diagnose()
    if not findings:
        p("  nothing wrong found")
    for f in findings:
        p(f"  {MARKS[f.level]} {f.title}" + (f"\n          you: {f.manual}" if f.manual and not f.fix else ""))
    if org is not None:
        p("\n== Health check ==")
        cfg = context["cfg"] or org.DEFAULT_CONFIG
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            with contextlib.suppress(Exception):
                org.run_doctor(cfg, full=True)
        p(buffer.getvalue().rstrip())
        p("\n== Settings (as stored) ==")
        data = load_json_file(CONFIG)
        p(json.dumps(data, indent=2) if data is not None else "  (unreadable or missing)")
        p("\n== Last runs ==")
        for entry in org.read_ledger()[-10:]:
            p("  " + json.dumps(entry))
        log = HISTORY / "organizer.log"
        p("\n== Last 40 log lines ==")
        if log.exists():
            p("\n".join(log.read_text(encoding="utf-8", errors="replace").splitlines()[-40:]))
    else:
        p(f"\norganizer.py could not be loaded: {error}")
    return redact(out.getvalue())


def cmd_report():
    path = HERE / "Organizer-report.txt"
    path.write_text(build_report(), encoding="utf-8")
    print(f"Saved {path}")
    print("It contains your settings, folder names and recent log lines (your user name is hidden).")
    print("Look it over, then send it along when asking for help.")
    return 0


# --------------------------------------------------------------------------- #
# Menu and command line
# --------------------------------------------------------------------------- #
def menu():
    print("=== Organizer 2.8 - repair ===")
    while True:
        print("""
 1) Check and repair everything (recommended)
 2) Only check - change nothing
 3) Restore my settings from a backup
 4) Reset settings to the defaults (a backup is kept)
 5) Save a support report (a text file to send when asking for help)
 0) Exit""")
        try:
            choice = input("Choose: ").strip()
        except (EOFError, KeyboardInterrupt):
            return 0
        print()
        org, _ = import_organizer()
        if choice in ("", "0"):
            return 0
        if choice == "1":
            cmd_fix()
        elif choice == "2":
            cmd_fix(check_only=True)
        elif choice == "5":
            cmd_report()
        elif choice in ("3", "4"):
            if org is None:
                print("organizer.py is damaged, so settings cannot be checked. " + UNZIP_HINT + ".")
            else:
                (cmd_restore if choice == "3" else cmd_reset)(org)
        else:
            print("Please type a number from the menu.")


def main(argv=None):
    parser = argparse.ArgumentParser(description="Repair Organizer.")
    parser.add_argument("--check", action="store_true", help="only look, change nothing")
    parser.add_argument("--fix", action="store_true", help="look, then fix")
    parser.add_argument("--yes", action="store_true", help="do not ask questions (never removes anything of yours)")
    parser.add_argument("--report", action="store_true", help="write Organizer-report.txt")
    args = parser.parse_args(argv)
    if args.report:
        return cmd_report()
    if args.check:
        return cmd_fix(check_only=True)
    if args.fix:
        return cmd_fix(assume_yes=args.yes)
    return menu()


if __name__ == "__main__":
    sys.exit(main())
