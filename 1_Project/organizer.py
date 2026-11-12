#!/usr/bin/env python3
"""
Organizer 2.7.1 (organizer.py) - a configurable, cross-platform folder organizer (stdlib only).

Features
  * Rule-based sorting: extension, filename glob, regex, file size
  * Your own folders: send specific files (a project's README, .bat, .xml, .exe ...) to a
      folder of your choice instead of the common type folders - manage them with
      manage_folders.py (menu) or by editing "rules" in the config
  * New file types get their own folder automatically: a file with no rule goes to Other/<EXT>
    (for example Other/DAT) instead of one big pile
  * Repair tool (repair.bat): checks everything and fixes what it safely can, with backups
  * Health check (--doctor / --status): is the scheduled task alive, when did it last run, any errors
  * Pause (--snooze 2h / --resume) for automatic runs, and a choice of how often they run
  * Space report (--space) and optional archiving of old installers/zips (--archive-old)
  * Loose FOLDERS are organized too (projects, photo folders, ...), but only once nothing inside
    has changed for a day, never venvs/node_modules, and always undoable
  * Several folders at once: list them under "watch" and run with --all
  * Suggestions: --suggest looks at your own files and proposes topic / project folders
  * Full run history: list every run, undo ANY run (not just the last) or put back single files
  * Duplicate finder: report identical files anywhere in a folder and optionally set the
    extra copies aside (always undoable)
  * Sub-folders inside each main folder, e.g. Images/PNG/2026-11 or Documents/Resumes
      - automatic: by extension, year, month, year-month, first letter, size
      - custom: nested "sub_rules" per rule (e.g. Documents -> Resumes, Invoices)
      - set globally, or override per rule
  * Smart duplicate detection: a file whose CONTENT is identical to one already in its destination
      folder - even under another name, like "report (1).pdf" - is set aside in _Duplicates
  * Safe conflict handling (rename / skip / overwrite)
  * Ignores hidden files and in-progress downloads (.crdownload, .part, ...)
  * Waits until a file is "settled" (min age) so it never moves a file mid-download
  * Dry-run mode, undo of the last run, watch mode, JSON config, logging

Where it runs
  By default it organizes the folder you run it FROM (your current folder), so one
  copy of this script can serve any folder: cd into the folder, run the script.
  Use -s to point it at a different folder instead.
  Safety: it refuses system folders, asks for confirmation, and stops on project
  folders (.git, package.json, ...) unless you pass --force.

Quick start
  python organizer.py --init-config          # writes organizer_config.json
  python organizer.py --dry-run              # preview for the current folder
  python D:/tools/organizer.py              # organize the current folder
  python organizer.py -s ~/Downloads         # organize a specific folder
  python organizer.py --watch --interval 60  # keep running
  python organizer.py --undo                 # reverse the last run
  python organizer.py -s ~/Desktop -r        # include sub-folders too
  python organizer.py -y                     # skip the confirmation prompt
"""

import argparse
import contextlib
import copy
import errno
import signal
import threading
import fnmatch
import functools
import hashlib
import html
import json
import logging
import logging.handlers
import os
import re
import shutil
import subprocess
import sys
import time
import uuid
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from pathlib import Path

__version__ = "2.7.1"

HISTORY_FILE = ".organizer_history.jsonl"   # legacy location (inside the organized folder)
SCRIPT_DIR = Path(__file__).resolve().parent
SKIP_DIR_NAMES = {"System Volume Information", "node_modules", "__pycache__", "venv", ".venv"}
# A folder counts as a "project" if it has any STRONG marker, or two or more WEAK ones.
# (A single downloaded Makefile or requirements.txt in Downloads is NOT a project.)
STRONG_MARKERS = [".git", ".hg", ".svn", "package.json", "pyproject.toml", "Cargo.toml",
                  "platformio.ini", "CMakeLists.txt", "pom.xml", "build.gradle"]
WEAK_MARKERS = ["Makefile", "requirements.txt", "setup.py"]
SYSTEM_DIRS_POSIX = ["/bin", "/boot", "/dev", "/etc", "/lib", "/lib64", "/proc", "/sbin",
                     "/sys", "/usr", "/var", "/System", "/Library", "/Applications"]
DEFAULT_CONFIG_NAME = "organizer_config.json"

DEFAULT_CONFIG = {
    "source": ".",                  # "." = the folder you run the script from
    "recursive": False,
    "min_age_seconds": 30,
    # Default sub-folders inside every main folder. Any combination, applied in order:
    # extension | year | month | year-month | first-letter | size   ([] = none)
    # A rule can override this with its own "subfolders" key.
    "subfolders": [],
    # Subject folders for the "topic" sub-folder mode: first topic with a matching word in the
    # file name wins. Files that match nothing stay at the level above (or go to topic_default).
    "topics": {
        "RTOS": ["rtos", "freertos", "zephyr"],
        "IoT": ["iot", "mqtt", "internet of things", "esp32"],
        "ARM": ["arm", "cortex", "thumb", "stm32"],
        "RISC-V": ["risc v", "riscv", "risc"],
        "Microcontrollers": ["microcontroller", "8051", "avr", "atmega"],
        "Resume": ["resume", "cv", "curriculum vitae"],
    },
    "topic_default": None,
    # Folders processed together by --all (the scheduled task uses it). Each entry is a path, or
    # {"path": "~/Desktop", "other_folder": null, ...} to override settings for that folder only.
    "watch": [],
    # What to do with loose FOLDERS in the organized folder (not the files inside them).
    # A folder is only moved when NOTHING inside it changed for min_age_hours, and never when
    # it holds a venv / node_modules (moving those breaks them). First matching rule wins:
    #   "contains": names to look for at the top of the folder (".git", "*.sln" ...)
    #   "mostly":   file types that make up at least "share" (default 0.6) of the files
    #   "patterns": globs for the folder's own name
    "folders": {
        "enabled": True,
        "dest": "Folders",
        "min_age_hours": 24,
        "skip_if_contains": ["pyvenv.cfg", "venv", ".venv", "node_modules"],
        "ignore": [],
        "unmatched": None,           # e.g. "Folders/Other" to sweep every loose folder
        "rules": [
            {"name": "Projects", "dest": "Folders/Projects",
             "contains": [".git", "package.json", "pyproject.toml", "platformio.ini", "CMakeLists.txt",
                          "Makefile", "*.ioc", "*.uvprojx", "*.sln", "*.ino"]},
            {"name": "Photos", "dest": "Folders/Photos", "min_files": 3,
             "mostly": [".jpg", ".jpeg", ".png", ".gif", ".webp", ".heic", ".bmp", ".tiff"]},
            {"name": "Videos", "dest": "Folders/Videos", "min_files": 2,
             "mostly": [".mp4", ".mkv", ".mov", ".avi", ".wmv", ".webm"]},
            {"name": "Audio", "dest": "Folders/Audio", "min_files": 3,
             "mostly": [".mp3", ".wav", ".flac", ".aac", ".ogg", ".m4a", ".opus", ".aiff", ".aif", ".mid", ".midi", ".wma"]},
            {"name": "Documents", "dest": "Folders/Documents", "min_files": 2,
             "mostly": [".pdf", ".docx", ".doc", ".pptx", ".ppt", ".xlsx", ".xls", ".csv", ".txt", ".odt", ".md"]},
            {"name": "Code", "dest": "Folders/Code", "min_files": 2,
             "mostly": [".py", ".c", ".cpp", ".h", ".hpp", ".java", ".js", ".ts", ".ino", ".v", ".vhd", ".asm"]},
        ],
    },
    "schedule_minutes": 30,          # how often the scheduled task runs (set by install.bat)
    # Old files can be moved (never deleted) to Archive/<year>/<rule name>/ . Off by default:
    # run  organizer.py --archive-old  by hand, or set "enabled": true to do it automatically
    # (at most once a day). "folder_rule" is the name of the file rule the files belong to.
    "cleanup": {
        "enabled": False,
        "archive_dest": "Archive",
        "rules": [
            {"name": "Installers", "folder_rule": "Installers", "older_than_days": 30},
            {"name": "Archives", "folder_rule": "Archives", "older_than_days": 60},
            {"name": "Disk images", "folder_rule": "Disk images", "older_than_days": 30},
        ],
    },
    "on_conflict": "rename",         # rename | skip | overwrite
    "dedupe_identical": True,        # identical files go to duplicates_folder
    "duplicates_folder": "_Duplicates",
    "other_folder": "Other",         # set to null to leave unmatched files alone
    # Files whose type has no rule get a folder named after the type: Other/DAT, Other/XYZ ...
    # "min_files": 1 = a folder for every new type at once; 3 = only once 3 such files exist
    # (smaller piles stay loose in Other/ until then, then are tidied into the new folder).
    "unknown_extensions": {"enabled": True, "min_files": 1},
    "ignore_hidden": True,
    "ignore_patterns": ["desktop.ini", "Thumbs.db", ".DS_Store", "*.lnk", "*password*.csv", "~$*"],
    "partial_extensions": [".crdownload", ".part", ".tmp", ".download", ".partial", ".opdownload"],
    "rules": [
        {"name": "Screenshots", "patterns": ["Screenshot*", "Screen Shot*"], "extensions": [".png", ".jpg", ".jpeg", ".webp", ".bmp"],
         "dest": "Images/Screenshots"},
        {"name": "Images", "extensions": [".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp", ".tiff", ".tif", ".svg", ".heic", ".ico", ".raw", ".cr2", ".nef", ".arw", ".dng", ".eps", ".jfif", ".avif"],
         "dest": "Images", "subfolders": ["extension"]},
        {"name": "Videos", "extensions": [".mp4", ".mkv", ".mov", ".avi", ".wmv", ".flv", ".webm", ".m4v", ".mpg", ".mpeg", ".3gp"], "dest": "Videos", "subfolders": ["extension"]},
        {"name": "Audio", "extensions": [".mp3", ".wav", ".flac", ".aac", ".ogg", ".m4a", ".opus", ".aiff", ".aif", ".mid", ".midi", ".wma"], "dest": "Audio", "subfolders": ["extension"]},
        {"name": "Build files", "patterns": ["Makefile", "GNUmakefile", "CMakeLists.txt", "*.mk", "*.cmake", "platformio.ini", "Dockerfile", "*.ld", "*.lds"],
         "dest": "Code/Build"},   # extension-less / special names; must stay above Documents
        {"name": "Documents", "extensions": [".pdf", ".docx", ".doc", ".pptx", ".ppt", ".odp", ".key", ".xlsx", ".xls", ".xlsm", ".xlsb", ".docm", ".dotx", ".pptm", ".csv", ".ods",
                        ".xml", ".txt", ".rtf", ".odt", ".md"],
         "dest": "Documents", "subfolders": ["extension", "topic"]},   # Documents/PDF, DOCX, PPTX, XLSX, CSV, XML ...
        {"name": "Ebooks", "extensions": [".epub", ".mobi", ".azw3"], "dest": "Ebooks"},
        {"name": "Archives", "extensions": [".zip", ".rar", ".7z", ".tar", ".gz", ".bz2", ".xz", ".tgz"], "dest": "Archives"},
        {"name": "Installers", "extensions": [".exe", ".msi", ".dmg", ".pkg", ".deb", ".rpm", ".apk", ".appimage"], "dest": "Installers"},
        {"name": "Disk images", "extensions": [".iso", ".img"], "dest": "Disk Images"},
        {"name": "Code", "extensions": [".py", ".c", ".cpp", ".h", ".hpp", ".java", ".js", ".ts", ".json", ".yaml", ".yml", ".sh", ".ino", ".v", ".vhd", ".asm", ".ipynb",
                        ".html", ".htm", ".css", ".scss", ".cs", ".go", ".rs", ".php", ".rb", ".swift", ".kt", ".sql", ".jsx", ".tsx", ".lua", ".toml"],
         "dest": "Code", "subfolders": ["extension"]},
        {"name": "Firmware", "extensions": [".hex", ".bin", ".elf", ".map", ".s19", ".srec", ".axf", ".uf2", ".lst"],
         "dest": "Firmware", "subfolders": ["extension"]},
        {"name": "Fonts", "extensions": [".ttf", ".otf", ".woff", ".woff2"], "dest": "Fonts"},
        {"name": "Design", "extensions": [".psd", ".ai", ".fig", ".sketch", ".xd", ".dwg", ".stl"], "dest": "Design"},
        {"name": "Torrents", "extensions": [".torrent"], "dest": "Torrents"},
        {"name": "Large files", "min_size_mb": 1024, "dest": "Large Files"},
    ],
}

log = logging.getLogger("organizer")


# --------------------------------------------------------------------------- #
# History (kept in <Organizer folder>/history, never inside the folders you organize)
# --------------------------------------------------------------------------- #
@functools.lru_cache(maxsize=1)
def history_dir():
    """<folder of this script>/history, or ~/Organizer/history if that is not writable."""
    for candidate in (SCRIPT_DIR / "history", Path.home() / "Organizer" / "history"):
        try:
            candidate.mkdir(parents=True, exist_ok=True)
            probe = candidate / ".write_test"
            probe.write_text("ok")
            probe.unlink()
            return candidate
        except OSError:
            continue
    return None


def history_path(base):
    """One history file per organized folder, e.g. history/Downloads_1a2b3c4d.jsonl"""
    folder = history_dir()
    if folder is None:
        return base / HISTORY_FILE  # last resort
    tag = hashlib.sha1(str(base).lower().encode("utf-8")).hexdigest()[:8]
    name = re.sub(r"[^A-Za-z0-9]+", "_", base.name or "root").strip("_")[:40] or "root"
    return folder / f"{name}_{tag}.jsonl"


def migrate_legacy_history(base):
    """Move an old .organizer_history.jsonl out of the organized folder."""
    legacy, target = base / HISTORY_FILE, history_path(base)
    if not legacy.exists() or legacy == target:
        return
    try:
        old = legacy.read_text(encoding="utf-8")
        new = target.read_text(encoding="utf-8") if target.exists() else ""
        target.write_text(old + new, encoding="utf-8")  # old runs first, newest last
        legacy.unlink()
        log.info("moved old history file into %s", target.parent)
    except OSError as exc:
        log.warning("could not move old history file: %s", exc)


# --------------------------------------------------------------------------- #
# Config
# --------------------------------------------------------------------------- #
def find_config(explicit):
    """-c file > organizer_config.json in the target folder > next to the script."""
    if explicit:
        p = Path(explicit).expanduser()
        if not p.exists():
            sys.exit(f"Config file not found: {p}")
        return p, True
    for folder in (Path.cwd(), Path(__file__).resolve().parent):
        candidate = folder / DEFAULT_CONFIG_NAME
        if candidate.exists():
            return candidate, False
    return None, False


def _fix_extension_dots(cfg):
    """A rule written as "extensions": ["pdf"] used to match nothing. Add the missing dots."""
    def fix(rule):
        exts = rule.get("extensions") if isinstance(rule, dict) else None
        if isinstance(exts, list) and any(isinstance(e, str) and e and not e.startswith(".") for e in exts):
            rule["extensions"] = [("." + e if isinstance(e, str) and e and not e.startswith(".") else e) for e in exts]
            log.warning('Rule "%s": added the missing dot to its extensions (write ".pdf", not "pdf").', rule.get("name", "?"))
        for sub in (rule.get("sub_rules", []) if isinstance(rule, dict) else []):
            fix(sub)
    rules = cfg.get("rules")
    if isinstance(rules, list):
        for rule in rules:
            fix(rule)


def load_config(explicit):
    """Returns (config, path of config used or None)."""
    cfg = json.loads(json.dumps(DEFAULT_CONFIG))  # deep copy
    path, is_explicit = find_config(explicit)
    if path:
        try:
            with open(path, "r", encoding="utf-8-sig") as fh:      # -sig: tolerate Notepad's hidden BOM
                user = json.load(fh)
        except ValueError as exc:
            message = f"{path} is damaged ({exc}). Double-click repair.bat to fix it."
            log.error(message)
            sys.exit(message)
        if not isinstance(user, dict):
            message = f"{path} must contain a JSON object {{ ... }}. Double-click repair.bat to fix it."
            log.error(message)
            sys.exit(message)
        if not is_explicit:
            user.pop("source", None)  # auto-found configs supply rules only, never the folder
        cfg.update(user)
    _fix_extension_dots(cfg)
    return cfg, path


def unblock_dir(base, dest):
    """A FILE (or a link) sitting where a destination folder must go - say a file called
    'Documents' - would make every move there fail. Use 'Documents (folder)' instead."""
    try:
        parts = Path(dest).relative_to(base).parts
    except ValueError:
        return Path(dest)                               # outside the organized folder: leave as is
    current = Path(base)
    for part in parts:
        candidate, number = current / part, 1
        while os.path.lexists(candidate) and (candidate.is_symlink() or not candidate.is_dir()):
            number += 1
            candidate = current / (f"{part} (folder)" if number == 2 else f"{part} (folder {number - 1})")
        current = candidate
    return current


def resolve_dest(base, dest):
    """Absolute / ~ paths are used as-is, relative ones live inside `base`."""
    d = Path(dest).expanduser()
    return d if d.is_absolute() else unblock_dir(base, base / d)


# --------------------------------------------------------------------------- #
# Matching
# --------------------------------------------------------------------------- #
_BAD_RULES = set()
_NESTED_REPEAT = re.compile(r"\((?:[^()\\]|\\.)*[+*](?:[^()\\]|\\.)*\)\s*(?:[+*]|\{\d*,\d*\})")


def regex_looks_slow(pattern):
    """True for patterns like (a+)+ that can take forever on a long name (nested repeats)."""
    return bool(_NESTED_REPEAT.search(pattern))


class _RegexTimeout(Exception):
    pass


def safe_regex_search(rule, name):
    """re.search with a 1 second limit (where the OS allows it); a rule that is too slow is switched off."""
    key = rule.get("name", "") + "|" + rule["regex"]
    if key in _BAD_RULES:
        return False
    use_alarm = hasattr(signal, "setitimer") and threading.current_thread() is threading.main_thread()
    old = None
    try:
        if use_alarm:
            def _handler(signum, frame):
                raise _RegexTimeout()
            old = signal.signal(signal.SIGALRM, _handler)
            signal.setitimer(signal.ITIMER_REAL, 1.0)
        try:
            return re.search(rule["regex"], name, re.IGNORECASE) is not None
        finally:
            if use_alarm:
                signal.setitimer(signal.ITIMER_REAL, 0)
                signal.signal(signal.SIGALRM, old)
    except _RegexTimeout:
        _BAD_RULES.add(key)
        log.warning('Rule "%s": the regex is too slow, so this rule is switched off for now. Simplify it.', rule.get("name", "?"))
        return False


def rule_matches(rule, path, size):
    name = path.name.lower()
    ext = "".join(path.suffixes[-1:]).lower()
    checks = []

    if "extensions" in rule:
        checks.append(ext in [e.lower() for e in rule["extensions"]])
    if "patterns" in rule:
        checks.append(any(fnmatch.fnmatch(name, p.lower()) for p in rule["patterns"]))
    if "regex" in rule:
        checks.append(safe_regex_search(rule, path.name))
    if "min_size_mb" in rule:
        checks.append(size >= rule["min_size_mb"] * 1024 * 1024)
    if "max_size_mb" in rule:
        checks.append(size <= rule["max_size_mb"] * 1024 * 1024)

    # all specified criteria must hold (AND); a rule with no criteria never matches
    return bool(checks) and all(checks)


SUBFOLDER_MODES = ["extension", "year", "month", "year-month", "first-letter", "size", "topic"]


def topic_parts(cfg, path):
    """Folder for the first subject in cfg["topics"] whose keyword appears in the file name.

    Case-insensitive; '_', '-', '.' and spaces count the same, and a keyword must not sit
    inside a longer word (so "arm" matches "ARM_Theory" but not "alarm").
    """
    text = re.sub(r"[^a-z0-9]+", " ", path.stem.lower())
    for topic, words in cfg.get("topics", {}).items():
        for word in words:
            word = re.sub(r"[^a-z0-9]+", " ", word.lower()).strip()
            if word and re.search(rf"(?<![a-z]){re.escape(word)}(?![a-z])", text):
                return [topic]
    default = cfg.get("topic_default")
    return [default] if default else []


def subfolder_parts(mode, path, size, cfg):
    """Return the folder name(s) a given sub-folder mode adds for this file."""
    mtime = datetime.fromtimestamp(path.stat().st_mtime)
    if mode == "extension":
        return [path.suffix.lstrip(".").upper() or "No Extension"]
    if mode == "year":
        return [f"{mtime:%Y}"]
    if mode == "month":
        return [f"{mtime:%Y-%m}"]
    if mode == "year-month":
        return [f"{mtime:%Y}", f"{mtime:%Y-%m}"]
    if mode == "first-letter":
        first = path.stem[:1].upper()
        return [first if first.isalpha() else "#"]
    if mode == "size":
        mb = size / (1024 * 1024)
        if mb < 1:
            return ["Small (under 1 MB)"]
        return ["Medium (1-100 MB)"] if mb < 100 else ["Large (100 MB+)"]
    if mode == "topic":
        return topic_parts(cfg, path)
    raise ValueError(f"Unknown subfolder mode: {mode}")


def add_subfolders(dest, modes, path, size, cfg):
    if isinstance(modes, str):
        modes = [modes]
    for mode in modes or []:
        for part in subfolder_parts(mode, path, size, cfg):
            dest = dest / part
    return dest


RESERVED_NAMES = {"con", "prn", "aux", "nul"} | {f"com{i}" for i in range(1, 10)} | {f"lpt{i}" for i in range(1, 10)}


def unknown_cfg(cfg):
    merged = copy.deepcopy(DEFAULT_CONFIG["unknown_extensions"])
    user = cfg.get("unknown_extensions")
    if isinstance(user, dict):
        merged.update(user)
    return merged


def extension_key(path):
    """The file type as a safe folder name ('dat'), or None if it cannot be one (no type, odd
    characters, or a name Windows reserves like CON / NUL)."""
    ext = path.suffix.lower().lstrip(".")
    if not re.fullmatch(r"[a-z0-9_+\-]{1,15}", ext) or ext in RESERVED_NAMES:
        return None
    return ext


def unknown_extension_folder(cfg, other_dest, path, counts):
    """Sub-folder of Other/ for a type with no rule, e.g. 'DAT' - or None to leave the file loose."""
    settings = unknown_cfg(cfg)
    ext = extension_key(path)
    if not settings["enabled"] or ext is None:
        return None
    name = ext.upper()
    if (other_dest / name).is_dir():                      # the folder already exists: keep using it
        return name
    seen = counts.get(ext, 1) if counts is not None else 1
    return name if seen >= settings["min_files"] else None


_WARNED = set()


def _dest_allowed(base, dest, rule):
    """A rule may only send files into the organized folder, unless it says "allow_outside": true
    (and even then never into a system location)."""
    if _inside(Path(os.path.normpath(str(dest))), base):
        return True
    ok = False
    if rule.get("allow_outside") is True:
        try:
            check_safe(Path(os.path.normpath(str(dest))), False, True)
            ok = True
        except SystemExit:
            ok = False
    if not ok and rule["name"] not in _WARNED:
        _WARNED.add(rule["name"])
        log.warning('Rule "%s" points outside the organized folder (%s), so it was not used. '
                    'Add "allow_outside": true to the rule if you really want that.', rule["name"], dest)
    return ok


def pick_destination(cfg, base, path, size, unknown_counts=None):
    """Return (final destination folder, label) or (None, None) to leave the file."""
    for rule in cfg["rules"]:
        if rule.get("enabled", True) is False or not rule_matches(rule, path, size):
            continue
        dest = resolve_dest(base, rule["dest"])
        if not _dest_allowed(base, dest, rule):
            continue
        label = rule["name"]
        for sub in rule.get("sub_rules", []):
            if rule_matches(sub, path, size):
                dest = dest / sub["dest"]
                label = f"{label}/{sub['name']}"
                break
        else:
            if rule.get("sub_default"):
                dest = dest / rule["sub_default"]
        modes = rule.get("subfolders", cfg.get("subfolders", []))
        return add_subfolders(dest, modes, path, size, cfg), label
    if cfg.get("other_folder"):
        dest = resolve_dest(base, cfg["other_folder"])
        kind = unknown_extension_folder(cfg, dest, path, unknown_counts)
        if kind:
            dest = dest / kind
        return add_subfolders(dest, cfg.get("subfolders", []), path, size, cfg), f"Other/{kind}" if kind else "Other"
    return None, None


def validate_config(cfg):
    """Fail early on a typo in a subfolder mode instead of erroring per file."""
    if cfg.get("on_conflict") not in {"rename", "skip", "overwrite"}:
        sys.exit("on_conflict must be rename, skip, or overwrite")
    if cfg.get("min_age_seconds", 0) < 0:
        sys.exit("min_age_seconds cannot be negative")
    for number, rule in enumerate(cfg["rules"], 1):
        if not isinstance(rule, dict) or "name" not in rule or "dest" not in rule:
            sys.exit(f'Rule #{number} in the config needs both a "name" and a "dest".')
        for key in ("extensions", "patterns"):
            if key in rule and not isinstance(rule[key], list):
                sys.exit(f'Rule "{rule["name"]}": "{key}" must be a list, e.g. ["README.md", "build.bat"].')
        if "regex" in rule:
            try:
                re.compile(rule["regex"])
            except re.error as exc:
                sys.exit(f'Rule "{rule["name"]}": invalid regex ({exc}).')
            if regex_looks_slow(rule["regex"]):
                log.warning('Rule "%s": the regex looks like it can run for ages (repeats inside repeats), '
                            'so this rule is switched off. Simplify it.', rule["name"])
                rule["enabled"] = False
        if not any(k in rule for k in ("extensions", "patterns", "regex", "min_size_mb", "max_size_mb")):
            log.warning('Rule "%s" has nothing to match on, so it will never be used.', rule["name"])
    unknown = cfg.get("unknown_extensions", {})
    if (not isinstance(unknown, dict) or not isinstance(unknown.get("enabled", True), bool)
            or not isinstance(unknown.get("min_files", 1), int) or isinstance(unknown.get("min_files", 1), bool)
            or unknown.get("min_files", 1) < 1):
        sys.exit('"unknown_extensions" must look like {"enabled": true, "min_files": 1} (min_files 1 or more).')
    minutes = cfg.get("schedule_minutes", 30)
    if not isinstance(minutes, int) or isinstance(minutes, bool) or not 1 <= minutes <= 1440:
        sys.exit('"schedule_minutes" must be a whole number of minutes between 1 and 1440.')
    if not isinstance(cfg.get("cleanup", {}), dict):
        sys.exit('"cleanup" must be a settings block like {"enabled": false, "rules": [...]}.')
    for number, rule in enumerate(cleanup_cfg(cfg)["rules"], 1):
        if (not isinstance(rule, dict) or "name" not in rule or "folder_rule" not in rule
                or not isinstance(rule.get("older_than_days"), (int, float))):
            sys.exit(f'Clean-up rule #{number} needs "name", "folder_rule" and a number "older_than_days".')
    watch = cfg.get("watch", [])
    if not isinstance(watch, list) or any(
            not (isinstance(w, str) or (isinstance(w, dict) and w.get("path"))) for w in watch):
        sys.exit('"watch" must be a list of folder paths, e.g. ["~/Downloads", "~/Desktop"].')
    if not isinstance(cfg.get("folders", {}), dict):
        sys.exit('"folders" must be a settings block like {"enabled": true, "min_age_hours": 24}.')
    for number, rule in enumerate(folders_cfg(cfg)["rules"], 1):
        if not isinstance(rule, dict) or "name" not in rule or "dest" not in rule:
            sys.exit(f'Folder rule #{number} needs both a "name" and a "dest".')
    topics = cfg.get("topics", {})
    if not isinstance(topics, dict) or any(not isinstance(v, list) for v in topics.values()):
        sys.exit('"topics" must look like {"RTOS": ["rtos", "freertos"], "IoT": ["iot", "mqtt"]}')
    all_modes = list(cfg.get("subfolders", []))
    for rule in cfg["rules"]:
        modes = rule.get("subfolders", [])
        all_modes += [modes] if isinstance(modes, str) else modes
    bad = [m for m in all_modes if m not in SUBFOLDER_MODES]
    if bad:
        sys.exit(f"Unknown subfolder mode(s): {', '.join(bad)}. Valid: {', '.join(SUBFOLDER_MODES)}")


# --------------------------------------------------------------------------- #
# File helpers
# --------------------------------------------------------------------------- #
def file_hash(path, chunk=1024 * 1024):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        while block := fh.read(chunk):
            h.update(block)
    return h.hexdigest()


def identical(a, b):
    try:
        if a.stat().st_size != b.stat().st_size:
            return False
        return file_hash(a) == file_hash(b)
    except OSError:
        return False


def _fit_name(stem, tail, suffix, limit=255):
    """stem + tail + suffix, with the stem shortened so the whole name stays within the 255 limit."""
    while len((stem + tail + suffix).encode("utf-8", "replace")) > limit and len(stem) > 1:
        stem = stem[:-1]
    return stem + tail + suffix


def unique_path(path):
    if not path.exists():
        return path
    stem, suffix, n = path.stem, path.suffix, 1
    while True:
        candidate = path.with_name(_fit_name(stem, f" ({n})", suffix))
        if not candidate.exists():
            return candidate
        n += 1


def human_size(n):
    for unit in ("bytes", "KB", "MB", "GB"):
        if n < 1024 or unit == "GB":
            return f"{n:.0f} {unit}" if unit == "bytes" else f"{n:.1f} {unit}"
        n /= 1024


class DupIndex:
    """Finds a file with IDENTICAL CONTENT already sitting in a destination folder, whatever
    its name. Cheap: only files of exactly the same size are ever read and hashed."""

    def __init__(self):
        self._sizes = {}    # folder -> {size: [files]}
        self._hashes = {}   # file -> sha256

    def _load(self, folder):
        if folder not in self._sizes:
            table = {}
            try:
                for item in folder.iterdir():
                    if item.is_file() and not item.is_symlink():
                        try:
                            table.setdefault(item.stat().st_size, []).append(item)
                        except OSError:
                            pass
            except OSError:
                pass        # the folder does not exist yet
            self._sizes[folder] = table
        return self._sizes[folder]

    def _hash(self, item):
        if item not in self._hashes:
            self._hashes[item] = file_hash(item)
        return self._hashes[item]

    def find(self, folder, path, size):
        if size == 0:       # empty files are all "identical"; that is not a useful duplicate
            return None
        candidates = [c for c in self._load(folder).get(size, []) if c != path]
        if not candidates:
            return None
        wanted = self._hash(path)
        for candidate in candidates:
            try:
                if self._hash(candidate) == wanted:
                    return candidate
            except OSError:
                continue
        return None

    def add(self, folder, item, size, known_hash_of=None):
        """Remember a file we just placed (or, in a dry run, would place) in `folder`."""
        self._load(folder).setdefault(size, []).append(item)
        if known_hash_of is not None and known_hash_of in self._hashes:
            self._hashes[item] = self._hashes[known_hash_of]


def safe_move(src, dst):
    """Move a file without ever leaving a half-finished copy behind.

    shutil.move() silently falls back to copy+delete when a rename fails, which on Windows
    (file still locked by the browser/antivirus) can leave a duplicate. Here a rename that
    fails for any reason except "different drive" is simply raised.
    """
    src, dst = str(src), str(dst)
    try:
        os.rename(src, dst)
    except OSError as exc:
        if isinstance(exc, PermissionError) or exc.errno != errno.EXDEV:
            raise
        shutil.copy2(src, dst)                      # different drive: copy, verify, then delete
        if os.path.getsize(src) != os.path.getsize(dst):
            os.unlink(dst)
            raise OSError("copy verification failed; original left untouched")
        try:
            os.unlink(src)
        except OSError:
            os.unlink(dst)                          # could not delete the original: undo the copy
            raise


def is_hidden(path):
    if path.name.startswith("."):
        return True
    if sys.platform.startswith("win"):
        try:
            return bool(path.stat().st_file_attributes & 0x2)   # FILE_ATTRIBUTE_HIDDEN
        except (AttributeError, OSError):
            return False
    return False


def _usable_mtime(st, now):
    """A date far in the future (wrong clock, odd download) counts as 'when the file arrived here'."""
    mtime = st.st_mtime
    if mtime > now + 120:
        mtime = min(getattr(st, "st_birthtime", None) or st.st_ctime, now)
    return mtime


def file_age(st):
    now = time.time()
    return now - _usable_mtime(st, now)


def should_skip(cfg, path, protected):
    name = path.name
    if name == HISTORY_FILE or name == Path(__file__).name or name == DEFAULT_CONFIG_NAME:
        return "internal file"
    if cfg.get("ignore_hidden") and is_hidden(path):
        return "hidden"
    if path.suffix.lower() in [e.lower() for e in cfg["partial_extensions"]]:
        return "partial download"
    if any(fnmatch.fnmatch(name.lower(), p.lower()) for p in cfg["ignore_patterns"]):
        return "ignored pattern"
    if any(parent in protected for parent in path.parents):
        return "already organized"
    age = file_age(path.stat())
    if age < cfg["min_age_seconds"]:
        return "too new (may still be downloading)"
    return None


def is_project_dir(path, extra_names=()):
    """True for a folder that must stay in one piece: a code project (.git, package.json ...) or
    anything holding a venv / node_modules. Recursive mode never takes these apart."""
    try:
        names = [n.lower() for n in os.listdir(path)]
    except OSError:
        return False
    markers = [m.lower() for m in list(STRONG_MARKERS) + list(extra_names)]
    return any(fnmatch.fnmatch(name, marker) for name in names for marker in markers)


def iter_files(base, recursive, protected, ignore_hidden, keep_whole=None):
    if not recursive:
        try:
            for p in base.iterdir():
                if not p.is_symlink() and p.is_file():
                    yield p
        except OSError as exc:
            log.error("cannot read %s: %s", base, exc)
        return
    stack = [base]
    while stack:
        current = stack.pop()
        try:
            children = list(current.iterdir())
        except OSError as exc:
            log.error("cannot read %s: %s", current, exc)
            continue
        for p in children:
            if p.is_dir():
                if (p.is_symlink() or p in protected or p.name in SKIP_DIR_NAMES or p.name.startswith("$")
                        or (ignore_hidden and p.name.startswith("."))
                        or (keep_whole is not None and keep_whole(p))):
                    continue
                stack.append(p)
            elif not p.is_symlink() and p.is_file():
                yield p


def protected_dirs(cfg, base):
    dirs = {resolve_dest(base, r["dest"]).resolve() for r in cfg["rules"]}
    if cfg.get("other_folder"):
        dirs.add(resolve_dest(base, cfg["other_folder"]).resolve())
    dirs.add(resolve_dest(base, cfg["duplicates_folder"]).resolve())
    fcfg = folders_cfg(cfg)
    dirs.add(resolve_dest(base, fcfg["dest"]).resolve())
    dirs.update(resolve_dest(base, r["dest"]).resolve() for r in fcfg["rules"])
    if fcfg.get("unmatched"):
        dirs.add(resolve_dest(base, fcfg["unmatched"]).resolve())
    history = history_dir()
    if history is not None:
        dirs.add(history.resolve())
    # protect top-level of nested destinations too (e.g. Documents for Documents/PDFs)
    for d in list(dirs):
        try:
            rel = d.relative_to(base.resolve())
            dirs.add((base.resolve() / rel.parts[0]))
        except (ValueError, IndexError):
            pass
    if SCRIPT_DIR != base.resolve() and _inside(SCRIPT_DIR, base.resolve()):
        dirs.add(SCRIPT_DIR)  # the Organizer folder (script, config, history) is never touched
    return dirs


# --------------------------------------------------------------------------- #
# Loose folders
# --------------------------------------------------------------------------- #
def folders_cfg(cfg):
    """The "folders" settings with any missing key filled in from the defaults."""
    merged = copy.deepcopy(DEFAULT_CONFIG["folders"])
    user = cfg.get("folders")
    if isinstance(user, dict):
        merged.update(user)
    return merged


def scan_folder(folder, limit=2000):
    """Look inside a folder (bounded): file count, types, newest change, names near the top."""
    exts, files, truncated = Counter(), 0, False
    try:
        newest = _usable_mtime(folder.stat(), time.time())
        top = [e.name for e in os.scandir(folder)]
    except OSError:
        return None
    names = set(top)
    stack = [(folder, 1)]
    while stack and not truncated:
        current, depth = stack.pop()
        try:
            entries = list(os.scandir(current))
        except OSError:
            continue
        for entry in entries:
            try:
                if entry.is_symlink():
                    continue
                stat = entry.stat(follow_symlinks=False)
                newest = max(newest, _usable_mtime(stat, time.time()))
                if depth <= 2:
                    names.add(entry.name)
                if entry.is_dir(follow_symlinks=False):
                    stack.append((Path(entry.path), depth + 1))
                else:
                    files += 1
                    exts[Path(entry.name).suffix.lower()] += 1
                    if files >= limit:
                        truncated = True
                        break
            except OSError:
                continue
    return {"files": files, "exts": exts, "newest": newest, "top": top, "names": names, "truncated": truncated}


def classify_folder(fcfg, folder, info):
    total = info["files"]
    for rule in fcfg["rules"]:
        if rule.get("enabled", True) is False:
            continue
        checks = []
        if "patterns" in rule:
            checks.append(any(fnmatch.fnmatch(folder.name.lower(), pat.lower()) for pat in rule["patterns"]))
        if "contains" in rule:
            checks.append(any(fnmatch.fnmatch(n.lower(), pat.lower())
                              for n in info["top"] for pat in rule["contains"]))
        if "mostly" in rule:
            wanted = {e.lower() for e in rule["mostly"]}
            hits = sum(count for ext, count in info["exts"].items() if ext in wanted)
            checks.append(total >= rule.get("min_files", 2) and total > 0
                          and hits / total >= rule.get("share", 0.6))
        if checks and all(checks):
            return rule
    return None


def folder_target(cfg, fcfg, base, folder):
    """Returns (destination folder, label, None) or (None, None, reason it was not moved)."""
    info = scan_folder(folder)
    if info is None:
        return None, None, "unreadable folder"
    if time.time() - info["newest"] < fcfg["min_age_hours"] * 3600:
        return None, None, "folder changed recently"
    skip_names = [pat.lower() for pat in fcfg["skip_if_contains"]]
    if any(fnmatch.fnmatch(n.lower(), pat) for n in info["names"] for pat in skip_names):
        return None, None, "folder has a venv/node_modules"
    rule = classify_folder(fcfg, folder, info)
    if rule:
        return resolve_dest(base, rule["dest"]), f"Folder: {rule['name']}", None
    if fcfg.get("unmatched"):
        return resolve_dest(base, fcfg["unmatched"]), "Folder: Other", None
    return None, None, "no folder rule"


def iter_candidate_folders(cfg, fcfg, base, protected):
    """Loose folders directly inside `base` that this program may consider moving."""
    try:
        children = sorted(base.iterdir())
    except OSError:
        return
    cwd = Path.cwd().resolve()
    ignore = [pat.lower() for pat in list(cfg.get("ignore_patterns", [])) + list(fcfg.get("ignore", []))]
    for item in children:
        try:
            if not item.is_dir() or item.is_symlink():
                continue
            real = item.resolve()
        except OSError:
            continue
        name = item.name
        if real in protected or name.startswith("$") or name in SKIP_DIR_NAMES:
            continue
        if cfg.get("ignore_hidden") and is_hidden(item):
            continue
        if any(fnmatch.fnmatch(name.lower(), pat) for pat in ignore):
            continue
        if _inside(SCRIPT_DIR, real) or _inside(cwd, real):      # holds the Organizer, or where we are running
            continue
        yield item


# --------------------------------------------------------------------------- #
# Core
# --------------------------------------------------------------------------- #
def write_history_entries(base, history):
    """Append the pending undo records to the history file and clear the list."""
    if not history:
        return
    try:
        with open(history_path(base), "a", encoding="utf-8") as fh:
            for entry in history:
                fh.write(json.dumps(entry) + "\n")
        history.clear()
    except OSError as exc:
        log.error("items were moved but the history could not be saved (undo unavailable): %s", exc)


def _permission_reason(exc):
    """Tell 'another program has it open' apart from 'you are not allowed to'."""
    code = getattr(exc, "winerror", None)
    if code in (32, 33):
        return "in use by another program, will retry next run"
    if code == 5:
        return "access denied (open in another program, or read-only), will retry next run"
    return "permission denied (check that the file and the folders are not read-only)"


def organize(cfg, base, dry_run=False):
    """One organizing pass. The undo records are written as the run goes (after every move) and
    again in `finally`, so a crash, Ctrl+C or a killed task cannot leave moves that cannot be undone."""
    history = []
    try:
        return _organize(cfg, base, dry_run, history)
    finally:
        write_history_entries(base, history)


def _organize(cfg, base, dry_run, history):
    if not dry_run and history_dir() is None:
        message = ("Nothing was moved: Organizer cannot save its undo history because its own folder is read-only. "
                   "Put the Organizer folder somewhere you can write to (for example D:\\Organizer_2.8) and run again.")
        log.error(message)
        sys.exit(message)
    if not dry_run:
        migrate_legacy_history(base)
    run_id = uuid.uuid4().hex[:8]
    protected = protected_dirs(cfg, base)
    aborted = False
    stats = {"moved": 0, "skipped": 0, "duplicates": 0, "errors": 0, "duplicate_bytes": 0}
    skip_reasons = Counter()
    moved_by_folder = Counter()
    index = DupIndex()

    keep_whole = lambda folder: is_project_dir(folder, folders_cfg(cfg)["skip_if_contains"])
    candidates = sorted(iter_files(base, cfg["recursive"], protected, cfg["ignore_hidden"], keep_whole))

    # How many files of each unknown type are there? (decides whether a type gets its own folder)
    unknown_counts, activated = Counter(), set()
    other_dest = resolve_dest(base, cfg["other_folder"]) if cfg.get("other_folder") else None
    if other_dest is not None and unknown_cfg(cfg)["enabled"] and unknown_cfg(cfg)["min_files"] > 1:
        for path in candidates:
            if should_skip(cfg, path, protected):
                continue
            try:
                _, label = pick_destination(cfg, base, path, path.stat().st_size)
            except OSError:
                continue
            if label and label.split("/")[0] == "Other" and extension_key(path):
                unknown_counts[extension_key(path)] += 1
        if other_dest.is_dir():                           # small piles left loose earlier count too
            for item in other_dest.iterdir():
                if item.is_file() and extension_key(item):
                    unknown_counts[extension_key(item)] += 1

    for path in candidates:
        if history:                                  # the previous move is saved before the next one starts
            write_history_entries(base, history)
        try:
            reason = should_skip(cfg, path, protected)
            if reason:
                log.debug("skip %s (%s)", path.name, reason)
                skip_reasons[reason] += 1
                stats["skipped"] += 1
                if reason.startswith("too new"):
                    log.info("waiting: %s (changed in the last %ds, still downloading?)",
                             path.name, cfg["min_age_seconds"])
                continue

            size = path.stat().st_size
            dest_dir, rule_name = pick_destination(cfg, base, path, size,
                                                   unknown_counts if unknown_counts else None)
            if rule_name and rule_name.startswith("Other/"):
                activated.add(rule_name.split("/", 1)[1].lower())
            if dest_dir is None:
                stats["skipped"] += 1
                continue
            dest_dir = unblock_dir(base, dest_dir)
            target = dest_dir / path.name

            twin = index.find(dest_dir, path, size) if cfg["dedupe_identical"] else None
            if twin is None and target.exists() and identical(path, target):
                twin = target
            if twin is not None:
                if cfg["dedupe_identical"]:
                    dest_dir = resolve_dest(base, cfg["duplicates_folder"])
                    target = unique_path(dest_dir / path.name)
                    rule_name = f"Duplicate of {twin.name}"
                    stats["duplicates"] += 1
                    stats["duplicate_bytes"] += size
                else:
                    stats["skipped"] += 1
                    continue
            elif target.exists():
                mode = cfg["on_conflict"]
                if mode == "skip":
                    log.info("conflict, skipping %s", path.name)
                    stats["skipped"] += 1
                    continue
                if mode == "rename":
                    original = target
                    target = unique_path(target)
                    log.info("%s already exists in %s - saved as %s", original.name, original.parent, target.name)
                elif mode == "overwrite":
                    backup = unique_path(target.with_name(
                        _fit_name(target.stem, f".backup-{run_id}", target.suffix)))
                    log.info("preserving overwritten file %s -> %s", target, backup)
                    if not dry_run:
                        backup.parent.mkdir(parents=True, exist_ok=True)
                        history.append({"run": run_id, "src": str(target), "dst": str(backup),
                                        "time": datetime.now().isoformat(timespec="seconds")})
                        write_history_entries(base, history)          # saved BEFORE the move (crash-proof)
                        safe_move(target, backup)

            log.info("%s%s -> %s  [%s]", "[dry-run] " if dry_run else "", path.name, target.parent, rule_name)
            if not dry_run:
                target.parent.mkdir(parents=True, exist_ok=True)
                history.append({"run": run_id, "src": str(path), "dst": str(target),
                                "time": datetime.now().isoformat(timespec="seconds")})
                write_history_entries(base, history)                  # saved BEFORE the move (crash-proof)
                safe_move(path, target)
            if not rule_name.startswith("Duplicate of"):
                moved_by_folder[rule_name.split("/")[0]] += 1
                index.add(target.parent, target if not dry_run else path, size, known_hash_of=path)
            stats["moved"] += 1
        except PermissionError as exc:
            reason = _permission_reason(exc)
            log.warning("%s: %s", reason, path.name)
            skip_reasons[reason.split(",")[0]] += 1
            stats["skipped"] += 1
        except Exception as exc:  # keep going if a single file fails
            if isinstance(exc, FileNotFoundError) and not os.path.lexists(path):
                skip_reasons["vanished while running"] += 1      # e.g. a browser deleted its temp file
                stats["skipped"] += 1
                continue
            stats["errors"] += 1
            if stats["errors"] <= 20:
                log.error("failed on %s: %s", path.name, exc)
            elif stats["errors"] == 21:
                log.error("more files are failing the same way - they are not all listed")
            if stats["errors"] >= 50 and stats["errors"] > 4 * (stats["moved"] + 1):
                log.error("stopping early because most files fail (last error: %s). Check that the folder "
                          "can be written to and the disk is not full.", exc)
                aborted = True
                break

    if activated and other_dest is not None and other_dest.is_dir() and not aborted:
        for item in sorted(other_dest.iterdir()):            # strays left loose when the pile was too small
            key = extension_key(item) if item.is_file() else None
            if key not in activated:
                continue
            target = unique_path(other_dest / key.upper() / item.name)
            log.info("%s%s -> %s  [Other/%s]", "[dry-run] " if dry_run else "", item.name, target.parent, key.upper())
            try:
                if not dry_run:
                    target.parent.mkdir(parents=True, exist_ok=True)
                    history.append({"run": run_id, "src": str(item), "dst": str(target),
                                    "time": datetime.now().isoformat(timespec="seconds")})
                    write_history_entries(base, history)
                    safe_move(item, target)
                moved_by_folder["Other"] += 1
                stats["moved"] += 1
            except OSError as exc:
                log.error("could not tidy %s: %s", item.name, exc)
                stats["errors"] += 1

    fcfg = folders_cfg(cfg)
    if fcfg["enabled"] and not cfg["recursive"] and not aborted:
        for folder in iter_candidate_folders(cfg, fcfg, base, protected):
            if history:
                write_history_entries(base, history)
            try:
                dest_dir, label, reason = folder_target(cfg, fcfg, base, folder)
                if dest_dir is None:
                    log.debug("folder %s left alone (%s)", folder.name, reason)
                    if reason != "no folder rule":
                        skip_reasons[reason] += 1
                        stats["skipped"] += 1
                    continue
                target = unique_path(dest_dir / folder.name)
                log.info("%s%s/ -> %s  [%s]", "[dry-run] " if dry_run else "", folder.name, target.parent, label)
                if not dry_run:
                    target.parent.mkdir(parents=True, exist_ok=True)
                    history.append({"run": run_id, "src": str(folder), "dst": str(target), "kind": "folder",
                                    "time": datetime.now().isoformat(timespec="seconds")})
                    write_history_entries(base, history)
                    os.rename(str(folder), str(target))          # a rename keeps the folder intact; never a copy
                moved_by_folder[label] += 1
                stats["moved"] += 1
            except PermissionError as exc:
                reason = _permission_reason(exc)
                log.warning("folder - %s: %s", reason, folder.name)
                skip_reasons[reason.split(",")[0]] += 1
                stats["skipped"] += 1
            except Exception as exc:
                stats["errors"] += 1
                if stats["errors"] <= 20:
                    log.error("failed on folder %s: %s", folder.name, exc)

    write_history_entries(base, history)
    stats["aborted"] = aborted

    if moved_by_folder:
        log.info("summary: %s", ", ".join(f"{n} {name}" for name, n in moved_by_folder.most_common()))
    if stats["duplicates"]:
        log.info("%d duplicate file(s) set aside in %s (%s) - once you have looked, delete that folder to free the space",
                 stats["duplicates"], cfg["duplicates_folder"], human_size(stats["duplicate_bytes"]))
    if dry_run and any(r.startswith("too new") for r in skip_reasons):
        log.info("tip: files younger than %d s are skipped on purpose; add --min-age 0 to preview them too.",
                 cfg["min_age_seconds"])
    detail = f" [{', '.join(f'{n} {r}' for r, n in skip_reasons.most_common())}]" if skip_reasons else ""
    log.info("done: %d moved (%d duplicates), %d skipped%s, %d errors",
             stats["moved"], stats["duplicates"], stats["skipped"], detail, stats["errors"])
    return stats


def _pid_alive(pid):
    """Is a process with this id still running? (never signals the process)"""
    if pid <= 0:
        return False
    if sys.platform.startswith("win"):
        try:
            import ctypes
            kernel = ctypes.windll.kernel32
            handle = kernel.OpenProcess(0x1000, False, pid)        # PROCESS_QUERY_LIMITED_INFORMATION
            if not handle:
                return ctypes.GetLastError() == 5                    # access denied = it exists
            code = ctypes.c_ulong()
            ok = kernel.GetExitCodeProcess(handle, ctypes.byref(code))
            kernel.CloseHandle(handle)
            return bool(ok) and code.value == 259                    # STILL_ACTIVE
        except Exception:
            return True
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError:
        return True
    return True


@contextlib.contextmanager
def run_lock(base):
    """Stops two runs (e.g. the scheduled one and a manual one) from working on a folder at once.
    Yields False if another run is active."""
    lock = history_path(base).with_suffix(".lock")
    state = "free"
    for _ in range(2):
        try:
            fd = os.open(str(lock), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            try:
                os.write(fd, str(os.getpid()).encode())
            finally:
                os.close(fd)
            state = "held"
            break
        except FileExistsError:
            try:
                owner = None
                try:
                    owner = int(lock.read_text().strip())
                except (OSError, ValueError):
                    pass
                too_old = time.time() - lock.stat().st_mtime > 900
                if too_old or (owner is not None and not _pid_alive(owner)):   # left behind by a crashed run
                    lock.unlink()
                    continue
            except OSError:
                pass
            state = "busy"
            break
        except OSError:
            break                                            # cannot lock: carry on without one
    try:
        yield state != "busy"
    finally:
        if state == "held":
            try:
                lock.unlink()
            except OSError:
                pass


DAMAGED_LINES = [0]


def read_history(base):
    migrate_legacy_history(base)
    hist = history_path(base)
    entries = []
    DAMAGED_LINES[0] = 0
    if hist.exists():
        for line in hist.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                entries.append(json.loads(line))
            except ValueError:
                DAMAGED_LINES[0] += 1
                log.warning("ignoring a damaged line in %s", hist.name)
    return hist, entries


def write_history(hist, entries):
    try:
        hist.write_text("".join(json.dumps(e) + "\n" for e in entries), encoding="utf-8")
    except OSError as exc:
        log.error("files were restored but the history could not be updated: %s", exc)


def restore_entry(entry, dry_run):
    """Move one file back where it came from. Returns True on success."""
    src, dst = Path(entry["src"]), Path(entry["dst"])
    if not dst.exists():
        if src.exists():                       # the record was saved just before a move that never happened
            log.debug("never moved (run was interrupted): %s", src.name)
            return None
        log.warning("missing, cannot restore: %s", dst)
        return False
    restore = unique_path(src) if src.exists() else src
    log.info("%s%s -> %s", "[dry-run] " if dry_run else "", dst.name, restore.parent)
    if not dry_run:
        try:
            restore.parent.mkdir(parents=True, exist_ok=True)
            safe_move(dst, restore)
        except OSError as exc:
            log.error("could not restore %s: %s", dst, exc)
            return False
    return True


def show_history(base):
    """Print every recorded run for this folder (read-only)."""
    _, entries = read_history(base)
    if not entries:
        print(f"No runs recorded yet for {base}")
        return
    runs = {}
    for entry in entries:
        runs.setdefault(entry["run"], []).append(entry)
    print(f"Runs recorded for {base} (oldest first):\n")
    for run_id, items in runs.items():
        when = items[0].get("time", "?").replace("T", " ")[:16]
        names = ", ".join(Path(i["dst"]).name for i in items[:2])
        more = f" +{len(items) - 2} more" if len(items) > 2 else ""
        print(f"  {run_id}   {when}   {len(items):>3} item(s)   {names}{more}")
    print("\nUndo the last run:      python organizer.py --undo")
    print("Undo a specific run:    python organizer.py --undo RUN_ID")
    print('Put back single files:  python organizer.py --restore "file name.pdf"')


def undo_run(base, dry_run=False, run_id=None):
    hist, entries = read_history(base)
    if not entries:
        log.info("nothing to undo for this folder%s", f" (no run '{run_id}' is recorded here)" if run_id else "")
        return
    if run_id is None:
        run_id = entries[-1]["run"]
    else:
        known = list(dict.fromkeys(e["run"] for e in entries))
        matches = [r for r in known if r == run_id or (len(run_id) >= 4 and r.startswith(run_id))]
        if len(matches) != 1:
            log.error("no single run matches '%s'. Runs: %s  (see --history)", run_id, ", ".join(known))
            return
        run_id = matches[0]

    chosen = [i for i, e in enumerate(entries) if e["run"] == run_id]
    failed = set()
    restored = 0
    for index in reversed(chosen):
        outcome = restore_entry(entries[index], dry_run)
        if outcome:
            restored += 1
            if not dry_run:
                _remove_empty_parents(Path(entries[index]["dst"]).parent, base)
        elif outcome is False:
            failed.add(index)
    if not dry_run:
        write_history(hist, [e for i, e in enumerate(entries) if i not in chosen or i in failed])
    log.info("%s run %s (%d item(s); %d could not be restored)",
             "would undo" if dry_run else "undid", run_id, restored, len(failed))
    if DAMAGED_LINES[0]:
        log.warning("%d damaged line(s) in the history could not be read, so those files (if any) were NOT put back.",
                    DAMAGED_LINES[0])


def _remove_empty_parents(folder, base):
    """After undo, remove the now-empty destination folders (never the organized folder itself)."""
    folder = Path(folder)
    while folder != base and _inside(folder, base):
        try:
            folder.rmdir()
        except OSError:
            break
        folder = folder.parent


def restore_files(base, names, dry_run=False):
    """Put individual files back, by the name they have now (wildcards allowed)."""
    hist, entries = read_history(base)
    wanted = [n.lower() for n in names]
    chosen, failed = [], set()
    for index in reversed(range(len(entries))):                   # newest first
        dst_name = Path(entries[index]["dst"]).name.lower()
        if any(fnmatch.fnmatch(dst_name, pattern) for pattern in wanted):
            chosen.append(index)
    if not chosen:
        log.info("no moved file in the history matches: %s", ", ".join(names))
        return
    restored = 0
    for index in chosen:
        outcome = restore_entry(entries[index], dry_run)
        if outcome:
            restored += 1
        elif outcome is False:
            failed.add(index)
    if not dry_run:
        write_history(hist, [e for i, e in enumerate(entries) if i not in chosen or i in failed])
    log.info("%s %d item(s)", "would restore" if dry_run else "restored", restored)


COPY_LOOKING = re.compile(r"(\(\d+\)|[ _-]copy( \(\d+\))?)\s*$", re.IGNORECASE)


def keeper_key(path):
    """Which copy to keep: not named like a copy, then nearest the top, shortest name, oldest."""
    try:
        mtime = path.stat().st_mtime
    except OSError:
        mtime = 0
    return (bool(COPY_LOOKING.search(path.stem)), len(path.parts), len(path.name), mtime, str(path).lower())


def scan_files(base, cfg, extra_skip=()):
    skip = {resolve_dest(base, cfg["duplicates_folder"]).resolve()}
    skip.update(Path(path).resolve() for path in extra_skip)
    if SCRIPT_DIR != base and _inside(SCRIPT_DIR, base):
        skip.add(SCRIPT_DIR)
    stack = [base]
    while stack:
        current = stack.pop()
        try:
            children = list(current.iterdir())
        except OSError:
            continue
        for item in children:
            if item.is_symlink() or is_hidden(item):
                continue
            if item.is_dir():
                if item.resolve() in skip or item.name in SKIP_DIR_NAMES or item.name.startswith("$"):
                    continue
                stack.append(item)
            elif item.is_file():
                yield item


def find_duplicates(cfg, base, set_aside=False, dry_run=False, assume_yes=False):
    """Report identical files anywhere under `base`. Changes nothing unless set_aside is True."""
    by_size, scanned = {}, 0
    for item in scan_files(base, cfg):
        try:
            size = item.stat().st_size
        except OSError:
            continue
        scanned += 1
        if size:                                                  # empty files are not useful duplicates
            by_size.setdefault(size, []).append(item)

    groups = []
    for size, files in by_size.items():
        if len(files) < 2:
            continue
        by_hash = {}
        for item in files:                                        # only same-size files are ever read
            try:
                by_hash.setdefault(file_hash(item), []).append(item)
            except OSError as exc:
                log.warning("could not read %s: %s", item, exc)
        groups += [(size, sorted(same, key=keeper_key)) for same in by_hash.values() if len(same) > 1]
    groups.sort(key=lambda g: g[0] * (len(g[1]) - 1), reverse=True)

    wasted = sum(size * (len(files) - 1) for size, files in groups)
    extras = sum(len(files) - 1 for _, files in groups)
    print(f"Scanned {scanned} files in {base}")
    if not groups:
        print("No duplicate files found.")
        return

    def rel(item):
        try:
            return str(item.relative_to(base))
        except ValueError:
            return str(item)

    print(f"Found {len(groups)} set(s) of identical files: {extras} extra copies using {human_size(wasted)}\n")
    for number, (size, files) in enumerate(groups, 1):
        print(f"{number:>3}) {human_size(size)} x {len(files)} copies")
        for position, item in enumerate(files):
            print(f"       {'keep ' if position == 0 else 'extra'}  {rel(item)}")
    if not set_aside:
        print("\nNothing was changed. To move the extra copies into "
              f"{cfg['duplicates_folder']} (undoable), add --set-aside.")
        return

    if not dry_run and not assume_yes and sys.stdin is not None and sys.stdin.isatty():
        answer = input(f"\nMove the {extras} extra copies to {cfg['duplicates_folder']}? [y/N] ")
        if answer.strip().lower() not in ("y", "yes"):
            print("Cancelled, nothing was moved.")
            return
    run_id = uuid.uuid4().hex[:8]
    dup_dir = resolve_dest(base, cfg["duplicates_folder"])
    history, moved = [], 0
    for _, files in groups:
        for item in files[1:]:
            target = unique_path(dup_dir / item.name)
            log.info("%s%s -> %s", "[dry-run] " if dry_run else "", rel(item), dup_dir)
            if dry_run:
                moved += 1
                continue
            try:
                target.parent.mkdir(parents=True, exist_ok=True)
                safe_move(item, target)
                history.append({"run": run_id, "src": str(item), "dst": str(target),
                                "time": datetime.now().isoformat(timespec="seconds")})
                moved += 1
            except OSError as exc:
                log.error("could not move %s: %s", item, exc)
    if history:
        try:
            with open(history_path(base), "a", encoding="utf-8") as fh:
                for entry in history:
                    fh.write(json.dumps(entry) + "\n")
        except OSError as exc:
            log.error("files were moved but the history could not be saved: %s", exc)
    log.info("%s %d extra copies (run %s); undo with: --undo",
             "would set aside" if dry_run else "set aside", moved, run_id)


def cleanup_empty_dirs(base, cfg):
    protected = protected_dirs(cfg, base)
    for d in sorted((p for p in base.rglob("*") if p.is_dir()), reverse=True):
        try:
            d.rmdir()  # only succeeds if empty (including empty category folders like Documents)
            log.info("removed empty folder %s", d)
        except OSError:
            pass


# --------------------------------------------------------------------------- #
# Safety
# --------------------------------------------------------------------------- #
def _inside(child, parent):
    try:
        child.relative_to(parent)
        return True
    except ValueError:
        return False


def check_safe(base, recursive, force):
    """Stop before touching places where organizing could do damage."""
    # Hard stops: system locations (cannot be overridden)
    if sys.platform.startswith("win"):
        system_drive = Path(os.environ.get("SystemDrive", "C:") + "\\").resolve()
        system_dirs = [Path(os.environ[k]).resolve() for k in
                       ("SystemRoot", "ProgramFiles", "ProgramFiles(x86)", "ProgramData") if os.environ.get(k)]
        if base == system_drive or any(_inside(base, d) for d in system_dirs):
            sys.exit(f"Refusing to organize a system location: {base}")
    elif base == Path("/") or any(_inside(base, Path(d)) for d in SYSTEM_DIRS_POSIX):
        sys.exit(f"Refusing to organize a system location: {base}")

    if force:
        return
    # Soft stops: allowed with --force
    problems = []
    if base == Path.home().resolve():
        problems.append("this is your home folder")
    if recursive and base == Path(base.anchor):
        problems.append("recursive mode on a whole drive")
    strong = [m for m in STRONG_MARKERS if (base / m).exists()]
    weak = [m for m in WEAK_MARKERS if (base / m).exists()]
    markers = strong + (weak if (strong or len(weak) >= 2) else [])
    if markers:
        problems.append(f"this looks like a project folder (found {', '.join(markers)})")
    if problems:
        sys.exit(f"Stopped: {'; '.join(problems)}. Use --force if you are sure.")


def confirm(base, cfg, args):
    if args.yes or args.dry_run or sys.stdin is None or not sys.stdin.isatty():
        return
    extra = " including all sub-folders" if cfg["recursive"] else ""
    if input(f"Organize {base}{extra}? [y/N] ").strip().lower() not in ("y", "yes"):
        sys.exit("Cancelled.")


# --------------------------------------------------------------------------- #
# Suggestions from your own files
# --------------------------------------------------------------------------- #
STOPWORDS = set("""
the and for with from you your are was this that not all but out has have had its into over than then them
they their there these those what when where which will would can could should about after before more most
some such only other also any one two new old final copy copies file files document documents doc docs
download downloads untitled image images img photo photos pic pics picture screenshot screen shot scan scanned
version draft backup test tests sample data text video videos audio setup install installer update release
attempt review practice exam paper full length points list entry instruction instructions
pdf docx xlsx pptx csv txt xml json html htm zip rar exe msi mp4 mkv mp3 wav jpg jpeg png gif webp
""".split())


def name_tokens(stem):
    """Lower-case words from a file name: CamelCase is split, trailing digits dropped (RTOS1 -> rtos)."""
    found = set()
    for chunk in re.split(r"[^A-Za-z0-9]+", stem):
        if not chunk:
            continue
        pieces = [chunk]
        if re.search(r"[a-z]", chunk) and re.search(r"[A-Z]", chunk[1:]):
            parts = re.findall(r"[A-Z]+(?![a-z])|[A-Z]?[a-z]+|\d+", chunk)
            if len(parts) > 1:
                pieces += parts
        for piece in pieces:
            word = re.sub(r"\d+$", "", piece.lower())
            if len(word) >= 3 and re.search(r"[a-z]{2}", word) and word not in STOPWORDS:
                found.add(word)
    return found


def known_words(cfg):
    """Words that already have a home, so they are not suggested again."""
    known = set(STOPWORDS)
    for topic, words in cfg.get("topics", {}).items():
        known.add(topic.lower())
        for word in words:
            known.update(re.sub(r"[^a-z0-9]+", " ", word.lower()).split())
    for rule in cfg["rules"]:
        known.add(rule.get("name", "").lower())
        for pattern in rule.get("patterns", []):
            known.update(re.findall(r"[a-z]{3,}", pattern.lower()))
    return known


def display_name(word):
    return word.upper() if len(word) <= 4 else word.capitalize()


def suggest_groups(cfg, base, min_files=3, limit=10):
    """Look at the file names under `base` and propose topic / project folders. Read-only.
    Returns (suggestions, number of files scanned)."""
    files = list(scan_files(base, cfg))
    total = len(files)
    known = known_words(cfg)
    index = defaultdict(set)
    for number, item in enumerate(files):
        for token in name_tokens(item.stem):
            index[token].add(number)

    best = {}                                    # one suggestion per identical set of files (longest word wins)
    for token, members in index.items():
        if token in known or len(members) < min_files:
            continue
        if total >= 12 and len(members) > 0.6 * total:
            continue                              # too common to be a subject
        key = frozenset(members)
        if key not in best or len(token) > len(best[key]):
            best[key] = token

    suggestions, covered = [], set()
    for members, token in sorted(best.items(), key=lambda kv: (-len(kv[0]), -len(kv[1]), kv[1])):
        if len(members - covered) < 0.5 * len(members):
            continue                              # mostly covered by a suggestion we already made
        covered |= members
        exts = Counter(files[i].suffix.lower() or "(none)" for i in members)
        rules = Counter()
        for i in sorted(members)[:60]:
            try:
                _, label = pick_destination(cfg, base, files[i], files[i].stat().st_size)
            except OSError:
                continue
            if label:
                rules[label.split("/")[0]] += 1
        rule_by_name = {r["name"]: r for r in cfg["rules"]}
        needs_topic = [name for name in rules if name in rule_by_name and "topic" not in
                       (rule_by_name[name].get("subfolders", cfg.get("subfolders", [])) or [])]
        suggestions.append({
            "name": display_name(token), "word": token, "count": len(members),
            "kind": "project" if len(exts) >= 3 else "topic",
            "types": sorted(exts), "rules": [r for r, _ in rules.most_common()],
            "needs_topic": needs_topic,
            "examples": [files[i].name for i in sorted(members)[:3]],
        })
        if len(suggestions) >= limit:
            break
    return suggestions, total


def apply_command(suggestion):
    if suggestion["kind"] == "project":
        return f'python manage_folders.py add {suggestion["name"]} --files {suggestion["word"]}'
    extra = f' --in {" ".join(suggestion["needs_topic"])}' if suggestion["needs_topic"] else ""
    return f'python manage_folders.py topic-add {suggestion["name"]} --words {suggestion["word"]}{extra}'


def print_suggestions(suggestions, scanned, base, min_files):
    print(f"Looked at {scanned} files in {base}")
    if not suggestions:
        print(f"No new subjects found (a word needs to appear in at least {min_files} file names).")
        return
    print(f"Words that show up in {min_files}+ file names and have no folder yet:\n")
    for number, item in enumerate(suggestions, 1):
        what = ("looks like a PROJECT: files of several types (" + " ".join(item["types"]) + ")"
                if item["kind"] == "project" else f"a SUBJECT: {', '.join(item['types'])} files")
        print(f"{number:>3}) {item['name']}  -  {item['count']} files, {what}")
        print(f"       e.g. {', '.join(item['examples'])}")
        print(f"       apply:  {apply_command(item)}")
    print("\nNothing was changed. The menu in folders.bat (option 7) can apply these for you.")


# --------------------------------------------------------------------------- #
# Run log, pause, health check
# --------------------------------------------------------------------------- #
TASK_NAME = "FolderOrganizer"            # must match setup_windows.py
LEDGER_NAME = "runs.jsonl"
PAUSE_NAME = "paused.json"


def cleanup_cfg(cfg):
    merged = copy.deepcopy(DEFAULT_CONFIG["cleanup"])
    user = cfg.get("cleanup")
    if isinstance(user, dict):
        merged.update(user)
    return merged


def human_ago(seconds):
    seconds = max(0, int(seconds))
    if seconds < 90:
        return "just now"
    minutes = seconds // 60
    if minutes < 90:
        return f"{minutes} minutes ago"
    hours = minutes // 60
    if hours < 48:
        return f"{hours} hours ago"
    return f"{hours // 24} days ago"


def ledger_path():
    folder = history_dir()
    return folder / LEDGER_NAME if folder else None


def record_run(base, stats, mode, status="ok"):
    """One line per real run (even when nothing moved) so --doctor can tell what happened when."""
    path = ledger_path()
    if path is None:
        return
    entry = {"time": datetime.now().isoformat(timespec="seconds"), "folder": str(base),
             "mode": mode, "status": status}
    for key in ("moved", "skipped", "errors", "duplicates"):
        entry[key] = int(stats.get(key, 0))
    try:
        with open(path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry) + "\n")
        if path.stat().st_size > 400_000:                      # keep the file small
            lines = path.read_text(encoding="utf-8").splitlines()[-1000:]
            path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    except OSError:
        pass


def read_ledger():
    path = ledger_path()
    entries = []
    if path is None or not path.exists():
        return entries
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return entries
    for line in text.splitlines():
        try:
            entries.append(json.loads(line))
        except ValueError:
            continue
    return entries


def parse_duration(text):
    """'30m', '2h', '1d' -> timedelta;  'forever' -> None."""
    text = text.strip().lower()
    if text in ("forever", "off", "indefinitely", "until-resumed"):
        return None
    match = re.fullmatch(r"(\d+)\s*(m|min|mins|minutes?|h|hr|hrs|hours?|d|days?)", text)
    if not match:
        raise ValueError(f'"{text}" is not a length of time. Use something like 30m, 2h, 1d or forever.')
    amount, unit = int(match.group(1)), match.group(2)[0]
    seconds = amount * {"m": 60, "h": 3600, "d": 86400}[unit]
    if not 0 < seconds <= 30 * 86400:
        raise ValueError("Choose between 1 minute and 30 days (or 'forever').")
    return timedelta(seconds=seconds)


def pause_path():
    folder = history_dir()
    return folder / PAUSE_NAME if folder else None


def set_pause(duration):
    path = pause_path()
    if path is None:
        raise OSError("there is no writable history folder to store the pause in")
    until = "forever" if duration is None else (datetime.now() + duration).isoformat(timespec="seconds")
    path.write_text(json.dumps({"until": until, "set": datetime.now().isoformat(timespec="seconds")}),
                    encoding="utf-8")
    return None if duration is None else datetime.fromisoformat(until)


def get_pause():
    """None when running normally; 'forever'; or the datetime the pause ends."""
    path = pause_path()
    if path is None or not path.exists():
        return None
    try:
        until = json.loads(path.read_text(encoding="utf-8"))["until"]
        if until == "forever":
            return "forever"
        ends = datetime.fromisoformat(until)
    except (OSError, ValueError, KeyError, TypeError):
        return None
    if ends <= datetime.now():
        try:
            path.unlink()
        except OSError:
            pass
        return None
    return ends


def clear_pause():
    path = pause_path()
    existed = path is not None and path.exists()
    if existed:
        try:
            path.unlink()
        except OSError:
            existed = False
    return existed


def describe_pause(pause):
    return "until you resume" if pause == "forever" else f"until {pause:%a %H:%M}"


def do_snooze(text):
    if text == "ask":
        if sys.stdin is None or not sys.stdin.isatty():
            sys.exit("Say for how long, e.g.  --snooze 2h   (30m, 2h, 1d or forever).")
        text = input("Pause automatic organizing for how long? (30m, 2h, 1d, forever) [1h]: ").strip() or "1h"
    try:
        duration = parse_duration(text)
        until = set_pause(duration)
    except (ValueError, OSError) as exc:
        sys.exit(str(exc))
    print(f"Automatic organizing is paused {describe_pause('forever' if until is None else until)}.")
    print("Organizing you start yourself (right-click menu, python organizer.py) still works.")
    print("Resume any time:  python organizer.py --resume   (or resume.bat)")


def do_resume():
    if clear_pause():
        print("Automatic organizing is on again.")
    else:
        print("It was not paused.")


def query_task():
    """Windows only. None = not Windows; otherwise what Task Scheduler says about our task."""
    if not sys.platform.startswith("win"):
        return None
    try:
        result = subprocess.run(["schtasks", "/Query", "/TN", TASK_NAME, "/XML"],
                                capture_output=True, text=True)
    except OSError as exc:
        return {"error": str(exc)}
    if result.returncode != 0:
        return {"installed": False}
    xml = result.stdout

    def tag(name):
        found = re.search(rf"<{name}>(.*?)</{name}>", xml, re.S)
        return html.unescape(found.group(1)).strip() if found else ""

    return {"installed": True, "command": tag("Command"), "arguments": tag("Arguments"),
            "enabled": "<Enabled>false</Enabled>" not in xml}


def query_menu():
    """Windows only: is the right-click entry installed and does it point at this copy?"""
    if not sys.platform.startswith("win"):
        return None
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                            r"Software\Classes\Directory\shell\FolderOrganizer\command") as key:
            value, _ = winreg.QueryValueEx(key, "")
    except OSError:
        return {"installed": False}
    return {"installed": True, "here": str(SCRIPT_DIR / "organizer.py").lower() in value.lower()}


def recent_log_problems(hours=24):
    """(errors, warning count) from history/organizer.log in the last `hours`."""
    folder = history_dir()
    path = folder / "organizer.log" if folder else None
    if path is None or not path.exists():
        return [], 0
    try:
        with open(path, "rb") as fh:
            fh.seek(0, os.SEEK_END)
            fh.seek(max(0, fh.tell() - 300_000))
            text = fh.read().decode("utf-8", "replace")
    except OSError:
        return [], 0
    line_re = re.compile(r"^(\d{4}-\d\d-\d\d \d\d:\d\d:\d\d)\s+(ERROR|WARNING)\s+(.*)$")
    cutoff = datetime.now() - timedelta(hours=hours)
    errors, warnings = [], 0
    for line in text.splitlines():
        match = line_re.match(line)
        if not match:
            continue
        try:
            when = datetime.strptime(match.group(1), "%Y-%m-%d %H:%M:%S")
        except ValueError:
            continue
        if when < cutoff:
            continue
        if match.group(2) == "ERROR":
            errors.append((match.group(1), match.group(3)))
        else:
            warnings += 1
    return errors, warnings


class Report:
    def __init__(self):
        self.problems = 0
        self.warnings = 0

    def head(self, title):
        print(f"\n{title}")

    def _line(self, mark, message, fix):
        print(f"  {mark}  {message}")
        if fix:
            print(f"          fix: {fix}")

    def ok(self, message):
        self._line("[ok]", message, None)

    def info(self, message):
        self._line("[..]", message, None)

    def warn(self, message, fix=None):
        self.warnings += 1
        self._line("[!] ", message, fix)

    def bad(self, message, fix=None):
        self.problems += 1
        self._line("[X] ", message, fix)


def run_doctor(cfg, full=True):
    """Plain-language check that everything works. Returns 0 (fine) or 1 (a real problem)."""
    r = Report()
    now = datetime.now()
    print(f"Organizer {__version__} - {'health check' if full else 'status'}")

    r.head("Automatic organizing")
    pause = get_pause()
    if pause:
        r.warn(f"PAUSED {describe_pause(pause)}: scheduled runs are skipped",
               "python organizer.py --resume   (or double-click resume.bat)")
    else:
        r.ok("not paused")
    try:
        interval = int(cfg.get("schedule_minutes", 30) or 30)
    except (TypeError, ValueError):
        interval = 30                                      # the settings check below reports the mistake
    try:
        validate_config(copy.deepcopy(cfg))
    except SystemExit as exc:                              # a broken settings file must never crash the check
        r.bad(f"the settings file has a mistake: {exc.code}", "fix it, or compare with the one in the zip")
    task = query_task()
    task_installed = False
    if task is None:
        r.info("scheduled task: not checked here (it only exists on Windows)")
    elif task.get("error"):
        r.warn(f"could not ask Windows about the scheduled task ({task['error']})")
    elif not task["installed"]:
        r.warn("the scheduled task is not installed, so nothing organizes by itself",
               "double-click install.bat")
    else:
        task_installed = True
        r.ok(f"scheduled task installed (every {interval} minutes)")
        if not task["enabled"]:
            r.bad("the scheduled task is switched OFF in Task Scheduler",
                  "enable the task 'FolderOrganizer' in Task Scheduler, or run install.bat again")
        if str(SCRIPT_DIR / "organizer.py").lower() not in task["arguments"].lower():
            r.bad("the scheduled task runs a different copy of Organizer:\n          " + task["arguments"],
                  "run install.bat from this folder to point it here")
        if task["command"] and not Path(task["command"]).exists():
            r.bad(f"Python was not found at {task['command']} (moved or uninstalled?)",
                  "run install.bat again")
        if "--all" not in task["arguments"]:
            r.warn("the task is from an older version and only handles one folder",
                   "run install.bat again to switch it to all watched folders")
    if full:
        menu = query_menu()
        if menu is None:
            pass
        elif not menu["installed"]:
            r.info("right-click menu: not installed (optional; install.bat adds it)")
        elif not menu["here"]:
            r.warn("the right-click menu points at a different copy of Organizer", "run install.bat again")
        else:
            r.ok("right-click menu installed")

    if full:
        r.head("Program and settings")
        r.ok(f"Organizer {__version__}, Python {sys.version_info.major}.{sys.version_info.minor}, in {SCRIPT_DIR}")
        if sys.version_info < (3, 8):
            r.bad("Python 3.8 or newer is needed", "install a newer Python from python.org")
        config_file, _ = find_config(None)
        r.ok(f"settings: {config_file or 'built-in defaults (no organizer_config.json found)'}")
        if history_dir() is None:
            r.bad("no writable history folder, so undo and this check cannot work",
                  f"make {SCRIPT_DIR / 'history'} writable")
        else:
            r.ok(f"history folder: {history_dir()}")

    r.head("Watched folders")
    entries = watch_entries(cfg)
    ledger = read_ledger()
    if not entries:
        r.warn("no folders are watched, so scheduled runs have nothing to do",
               'python manage_folders.py watch-add "C:\\Users\\you\\Downloads"  (or folders.bat, option 8)')
    for path, _ in entries:
        base = Path(path).expanduser()
        if not base.is_dir():
            r.bad(f"{base}: folder not found", "folders.bat, option 8 (remove it or fix the path)")
            continue
        resolved = str(base.resolve()).lower()
        mine = [e for e in ledger if str(e.get("folder", "")).lower() == resolved]
        last = mine[-1] if mine else None
        if full:
            if not os.access(base, os.W_OK):
                r.bad(f"{base}: Organizer is not allowed to change this folder")
            try:
                free = shutil.disk_usage(base).free
                if free < 1024 ** 3:
                    r.warn(f"{base}: only {human_size(free)} free on this drive")
            except OSError:
                pass
        if last is None:
            r.info(f"{base}: never organized by Organizer yet")
        else:
            age = (now - datetime.fromisoformat(last["time"])).total_seconds()
            detail = f"{last.get('moved', 0)} moved, {last.get('errors', 0)} errors"
            line = f"{base}: last run {human_ago(age)} ({last.get('mode', '?')}, {last.get('status', 'ok')}), {detail}"
            (r.warn if last.get("errors") else r.ok)(line)
        if task_installed and not pause:
            scheduled = [e for e in mine if e.get("mode") == "scheduled"]
            if scheduled:
                since = (now - datetime.fromisoformat(scheduled[-1]["time"])).total_seconds()
                if since > (3 * interval + 10) * 60:
                    r.warn(f"{base}: the last scheduled run was {human_ago(since)} (expected every {interval} minutes)",
                           "was the PC off or asleep? otherwise check Task Scheduler or run install.bat again")
            else:
                r.info(f"{base}: the scheduled task has not run on it yet")

    if full:
        r.head("Recent problems")
        errors, warnings = recent_log_problems()
        if errors:
            r.warn(f"{len(errors)} error(s) in the last 24 hours; the latest:")
            for when, message in errors[-3:]:
                print(f"          {when}  {message[:100]}")
            print(f"          (full log: {history_dir() / 'organizer.log' if history_dir() else 'n/a'})")
        else:
            r.ok("no errors in the last 24 hours" + (f" ({warnings} warning(s))" if warnings else ""))
        folder = history_dir()
        stale = []
        if folder:
            for lock in folder.glob("*.lock"):
                try:
                    if time.time() - lock.stat().st_mtime > 900:
                        stale.append(lock)
                except OSError:
                    pass
        if stale:
            r.warn(f"{len(stale)} stale lock file(s) from a crashed run", f"delete: {stale[0]}")
        ccfg = cleanup_cfg(cfg)
        r.info("clean-up of old files: " + ("ON (archives old installers/zips once a day)"
                                            if ccfg["enabled"] else "off (use --space to see what it would free)"))

    print()
    if r.problems:
        print(f"{r.problems} problem(s) and {r.warnings} warning(s) - see the lines marked [X] and [!].")
    elif r.warnings:
        print(f"Working, with {r.warnings} thing(s) to look at - see the lines marked [!].")
    else:
        print("Everything looks good.")
    if r.problems or r.warnings:
        print("To fix what can be fixed automatically: double-click repair.bat")
    if not full:
        print("For a full check:  python organizer.py --doctor   (or doctor.bat)")
    return 1 if r.problems else 0


# --------------------------------------------------------------------------- #
# Space report and clean-up of old files
# --------------------------------------------------------------------------- #
def newest_stamp(stat):
    """When the file last changed or arrived (whichever is later): a fresh download of an old
    file counts as new."""
    stamps = [stat.st_mtime]
    birth = getattr(stat, "st_birthtime", None)
    if birth is None and sys.platform.startswith("win"):
        birth = stat.st_ctime
    if birth:
        stamps.append(birth)
    return max(stamps)


def folder_size(folder):
    total = 0
    try:
        for root, _dirs, names in os.walk(folder):
            for name in names:
                try:
                    total += os.lstat(os.path.join(root, name)).st_size
                except OSError:
                    pass
    except OSError:
        pass
    return total


def gather_files(cfg, base):
    """[(size, path, stamp)] for every file under base (hidden / duplicates / the Organizer excluded)."""
    found = []
    for item in scan_files(base, cfg):
        try:
            stat = item.stat()
        except OSError:
            continue
        found.append((stat.st_size, item, newest_stamp(stat)))
    return found


def plan_archive(cfg, base, files):
    """Old files that sit in the organized folder a clean-up rule is about (for example
    Installers/). Where a file IS decides, never what it looks like: installers inside your
    own project folders, or inside Folders/, are never touched."""
    ccfg = cleanup_cfg(cfg)
    file_rules = {r["name"]: r for r in cfg["rules"]}
    archive_root = resolve_dest(base, ccfg["archive_dest"])
    homes = []
    for rule in ccfg["rules"]:
        if rule.get("enabled", True) is False:
            continue
        target = file_rules.get(rule["folder_rule"])
        if target is None:
            log.debug("clean-up rule %s refers to unknown folder rule %s", rule["name"], rule["folder_rule"])
            continue
        homes.append((resolve_dest(base, target["dest"]), rule))
    now, plan = time.time(), []
    for size, item, stamp in files:
        if _inside(item, archive_root):
            continue
        for home, rule in homes:
            if _inside(item, home) and now - stamp >= rule["older_than_days"] * 86400:
                plan.append((size, item, rule, stamp))
                break
    return plan


def space_report(cfg, base, top=10):
    files = gather_files(cfg, base)
    total = sum(size for size, _, _ in files)
    now = time.time()
    print(f"Space report for {base}: {len(files)} files, {human_size(total)}\n")

    groups = defaultdict(lambda: [0, 0])
    for size, item, _ in files:
        parts = item.relative_to(base).parts
        key = parts[0] if len(parts) > 1 else "(loose files)"
        groups[key][0] += size
        groups[key][1] += 1
    print("By folder:")
    for name, (size, count) in sorted(groups.items(), key=lambda kv: -kv[1][0])[:12]:
        print(f"  {human_size(size):>10}   {count:>5} files   {name}")

    duplicates = folder_size(resolve_dest(base, cfg["duplicates_folder"]))
    if duplicates:
        print(f"\nThe {cfg['duplicates_folder']} folder holds {human_size(duplicates)} of duplicates - "
              "safe to delete once you have looked inside.")

    print(f"\nBiggest {top} files:")
    for size, item, stamp in sorted(files, key=lambda f: -f[0])[:top]:
        print(f"  {human_size(size):>10}   {human_ago(now - stamp):<14} {item.relative_to(base)}")

    plan = plan_archive(cfg, base, files)
    ccfg = cleanup_cfg(cfg)
    print("\nOld files that clean-up could move to " + f"{ccfg['archive_dest']}/ (nothing is ever deleted):")
    if not plan:
        print("  none right now")
    else:
        by_rule = defaultdict(lambda: [0, 0])
        for size, _, rule, _ in plan:
            by_rule[rule["name"]][0] += size
            by_rule[rule["name"]][1] += 1
        days = {r["name"]: r["older_than_days"] for r in ccfg["rules"]}
        for name, (size, count) in sorted(by_rule.items(), key=lambda kv: -kv[1][0]):
            print(f"  {human_size(size):>10}   {count:>5} files   {name} older than {days[name]} days")
        print(f"\nMove them with:  python organizer.py --archive-old   (add --dry-run to preview)")
    print("Find identical copies with:  python organizer.py --find-duplicates")


def archive_old(cfg, base, dry_run=False, assume_yes=False, say=print, files=None):
    """Move old installers/zips/disk images (per the cleanup rules) into Archive/<year>/<rule>/."""
    files = gather_files(cfg, base) if files is None else files
    plan = plan_archive(cfg, base, files)
    if not plan:
        say("no old files to archive")
        return 0
    total = sum(size for size, _, _, _ in plan)
    say(f"{len(plan)} old file(s), {human_size(total)}, {'would be' if dry_run else 'to be'} archived")
    ccfg = cleanup_cfg(cfg)
    archive_root = resolve_dest(base, ccfg["archive_dest"])
    if dry_run:
        for size, item, rule, stamp in plan[:15]:
            say(f"[dry-run] {item.relative_to(base)} -> {ccfg['archive_dest']}/{datetime.fromtimestamp(stamp).year}/{rule['name']}")
        return len(plan)
    if not assume_yes and sys.stdin is not None and sys.stdin.isatty():
        if input(f"Move these {len(plan)} files into {archive_root}? [y/N] ").strip().lower() not in ("y", "yes"):
            say("cancelled, nothing was moved")
            return 0
    run_id, history, moved = uuid.uuid4().hex[:8], [], 0
    for size, item, rule, stamp in plan:
        target = unique_path(archive_root / str(datetime.fromtimestamp(stamp).year) / rule["name"] / item.name)
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            safe_move(item, target)
            history.append({"run": run_id, "src": str(item), "dst": str(target),
                            "time": datetime.now().isoformat(timespec="seconds")})
            moved += 1
        except OSError as exc:
            log.error("could not archive %s: %s", item, exc)
    if history:
        try:
            with open(history_path(base), "a", encoding="utf-8") as fh:
                for entry in history:
                    fh.write(json.dumps(entry) + "\n")
        except OSError as exc:
            log.error("files were archived but the history could not be saved: %s", exc)
    say(f"archived {moved} old file(s) (run {run_id}); undo with: --undo")
    return moved


def maybe_auto_archive(cfg, base, dry_run):
    """Automatic clean-up when "cleanup": {"enabled": true}: at most once every 24 hours per folder."""
    if not cleanup_cfg(cfg)["enabled"] or dry_run:
        return
    stamp = history_path(base).with_suffix(".archive")
    try:
        if stamp.exists() and time.time() - stamp.stat().st_mtime < 24 * 3600:
            return
        archive_old(cfg, base, assume_yes=True, say=log.info)
        stamp.write_text(datetime.now().isoformat(), encoding="utf-8")
    except OSError as exc:
        log.warning("clean-up skipped: %s", exc)


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def parse_args():
    p = argparse.ArgumentParser(description="Organize a folder automatically.")
    p.add_argument("-s", "--source", help="folder to organize (default: the folder you run the script from)")
    p.add_argument("-c", "--config", help="JSON config file (default: organizer_config.json in the target folder or next to the script)")
    p.add_argument("-r", "--recursive", action="store_true", help="also process sub-folders")
    p.add_argument("-n", "--dry-run", action="store_true", help="show what would happen, move nothing")
    p.add_argument("--subfolders", nargs="+", choices=SUBFOLDER_MODES + ["none"],
                   help="sub-folders inside each main folder, applied in order "
                        "(e.g. --subfolders extension year); overrides per-rule settings; 'none' disables")
    p.add_argument("--on-conflict", choices=["rename", "skip", "overwrite"])
    p.add_argument("--min-age", type=int, help="seconds a file must be untouched before moving")
    p.add_argument("--clean-empty", action="store_true", help="remove empty sub-folders afterwards")
    p.add_argument("-w", "--watch", action="store_true", help="keep running and organize repeatedly")
    p.add_argument("--interval", type=int, default=60, help="seconds between passes in watch mode")
    p.add_argument("--undo", nargs="?", const="last", metavar="RUN_ID",
                   help="reverse the last run, or the run with this id (see --history)")
    p.add_argument("--history", action="store_true", help="list the runs recorded for the folder")
    p.add_argument("--restore", nargs="+", metavar="FILE",
                   help="put individual files back where they came from (by their current name; wildcards ok)")
    p.add_argument("--find-duplicates", action="store_true",
                   help="report identical files anywhere in the folder (changes nothing)")
    p.add_argument("--set-aside", action="store_true",
                   help="with --find-duplicates: move the extra copies into the duplicates folder")
    p.add_argument("--doctor", action="store_true", help="full health check in plain language")
    p.add_argument("--status", action="store_true", help="short status: pause, last runs")
    p.add_argument("--snooze", nargs="?", const="ask", metavar="DURATION",
                   help="pause AUTOMATIC organizing for e.g. 30m, 2h, 1d or forever")
    p.add_argument("--resume", action="store_true", help="turn automatic organizing back on")
    p.add_argument("--space", action="store_true", help="report what takes up space and what could be archived")
    p.add_argument("--archive-old", action="store_true",
                   help="move old installers / zips / disk images to Archive/<year>/ (never deletes)")
    p.add_argument("--scheduled", action="store_true", help=argparse.SUPPRESS)
    p.add_argument("-a", "--all", action="store_true",
                   help='work on every folder listed under "watch" in the config (the scheduled task uses this)')
    p.add_argument("--suggest", action="store_true",
                   help="look at your own files and propose topic / project folders (changes nothing)")
    p.add_argument("--min-files", type=int, default=3, metavar="N",
                   help="with --suggest: a word must appear in at least N file names (default 3)")
    p.add_argument("--init-config", action="store_true", help=f"write {DEFAULT_CONFIG_NAME} and exit")
    p.add_argument("--log-file", help="also write logs to this file")
    p.add_argument("--version", action="version", version=f"Organizer {__version__}")
    p.add_argument("--pause", action="store_true", help="wait for Enter before closing (used by the right-click menu)")
    p.add_argument("-y", "--yes", action="store_true", help="do not ask for confirmation")
    p.add_argument("--force", action="store_true", help="allow project folders, home folder, etc.")
    p.add_argument("-v", "--verbose", action="store_true")
    return p.parse_args()


class _SafeText(logging.Filter):
    """File names with undecodable bytes must never break a log line."""
    def filter(self, record):
        try:
            text = record.getMessage()
        except Exception:
            text = str(record.msg)
        record.msg = text.encode("utf-8", "backslashreplace").decode("utf-8", "replace")
        record.args = ()
        return True


def setup_logging(verbose, log_file):
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(errors="backslashreplace")
        except Exception:
            pass
    console = logging.StreamHandler()
    console.setFormatter(logging.Formatter("%(asctime)s  %(message)s", "%H:%M:%S"))
    handlers = [console]
    file_format = logging.Formatter("%(asctime)s  %(levelname)-7s %(message)s", "%Y-%m-%d %H:%M:%S")
    folder = history_dir()
    if folder is not None:
        try:
            handlers.append(logging.handlers.RotatingFileHandler(
                folder / "organizer.log", maxBytes=1_000_000, backupCount=3, encoding="utf-8"))
        except OSError as exc:                      # log file locked or not ours: carry on without it
            print(f"note: could not open the log file ({exc}); continuing without it", file=sys.stderr)
    if log_file:
        handlers.append(logging.FileHandler(log_file, encoding="utf-8"))
    for handler in handlers:
        handler.addFilter(_SafeText())
    for handler in handlers[1:]:
        handler.setFormatter(file_format)
    logging.basicConfig(level=logging.DEBUG if verbose else logging.INFO, handlers=handlers)


def apply_cli(cfg, args):
    """Command-line switches win over the config file."""
    if args.recursive:
        cfg["recursive"] = True
    if args.subfolders:
        cfg["subfolders"] = [] if args.subfolders == ["none"] else args.subfolders
        for rule in cfg["rules"]:       # the command line wins over per-rule settings
            rule.pop("subfolders", None)
    if args.on_conflict:
        cfg["on_conflict"] = args.on_conflict
    if args.min_age is not None:
        cfg["min_age_seconds"] = args.min_age


def watch_entries(cfg):
    """[(path, overrides)] from the "watch" list; duplicates removed."""
    entries, seen = [], set()
    watch = cfg.get("watch", [])
    for entry in watch if isinstance(watch, list) else []:
        path, overrides = (entry, {}) if isinstance(entry, str) else (
            entry["path"], {k: v for k, v in entry.items() if k != "path"})
        key = str(Path(path).expanduser()).lower()
        if key not in seen:
            seen.add(key)
            entries.append((path, overrides))
    return entries


def prepare_targets(args, base_cfg):
    """[(config, folder)] to work on: the one folder asked for, or every watched folder."""
    if args.all and args.source:
        sys.exit("Use either --all (every watched folder) or -s (one folder), not both.")
    if args.all:
        sources = watch_entries(base_cfg)
        if not sources and getattr(args, "scheduled", False):
            log.info("no watched folders are set up, nothing to do")
            return []
        if not sources:
            sys.exit('No folders are listed under "watch" in the config. Add one with:\n'
                     '  python manage_folders.py watch-add "C:\\Users\\you\\Downloads"')
    else:
        sources = [(args.source or base_cfg["source"], {})]
    targets = []
    for path, overrides in sources:
        cfg = copy.deepcopy(base_cfg)
        cfg.update(overrides)
        cfg["source"] = path
        apply_cli(cfg, args)
        validate_config(cfg)
        base = Path(path).expanduser().resolve()
        if not base.is_dir():
            if args.all:
                log.warning("watched folder not found, skipping: %s", base)
                continue
            sys.exit(f"Source folder does not exist: {base}")
        targets.append((cfg, base))
    return targets


def run_command(cfg, base, args):
    """History / undo / restore / duplicates / suggestions for one folder."""
    if args.history:
        show_history(base)
    elif args.restore:
        restore_files(base, args.restore, args.dry_run)
    elif args.undo:
        undo_run(base, args.dry_run, None if args.undo == "last" else args.undo)
    elif args.suggest:
        suggestions, scanned = suggest_groups(cfg, base, args.min_files)
        print_suggestions(suggestions, scanned, base, args.min_files)
    elif args.space:
        space_report(cfg, base)
    elif args.archive_old:
        check_safe(base, True, args.force)
        guard = contextlib.nullcontext(True) if args.dry_run else run_lock(base)
        with guard as free:
            if free:
                archive_old(cfg, base, args.dry_run, args.yes)
            else:
                log.info("another run is already working on this folder, try again in a moment")
    else:
        if args.set_aside:
            check_safe(base, True, args.force)
        guard = contextlib.nullcontext(True) if (args.dry_run or not args.set_aside) else run_lock(base)
        with guard as free:
            if free:
                find_duplicates(cfg, base, args.set_aside, args.dry_run, args.yes)
            else:
                log.info("another run is already working on this folder, try again in a moment")


def run_mode(args):
    return "scheduled" if args.scheduled else ("watch" if args.watch else "manual")


def organize_one(cfg, base, args):
    mode = run_mode(args)
    pause = None if args.dry_run else get_pause()
    if pause and mode != "manual":
        log.info("automatic organizing is paused %s - skipping %s", describe_pause(pause), base)
        record_run(base, {}, mode, "paused")
        return
    if pause:
        log.info("(automatic organizing is paused %s; this run you started yourself goes ahead)",
                 describe_pause(pause))
    log.info("organizing %s%s", base, " (dry run)" if args.dry_run else "")
    guard = contextlib.nullcontext(True) if args.dry_run else run_lock(base)
    with guard as free:
        if not free:
            log.info("another run is already working on this folder, skipping this one")
            if not args.dry_run:
                record_run(base, {}, mode, "busy")
            return
        try:
            stats = organize(cfg, base, args.dry_run)
        except Exception:
            if not args.dry_run:
                record_run(base, {}, mode, "error")
            raise
        if not args.dry_run:
            record_run(base, stats, mode, "stopped" if stats.get("aborted") else "ok")
        if args.clean_empty and not args.dry_run:
            cleanup_empty_dirs(base, cfg)
        maybe_auto_archive(cfg, base, args.dry_run)


def confirm_all(prepared, args):
    if args.yes or args.dry_run or sys.stdin is None or not sys.stdin.isatty():
        return
    listing = "\n  ".join(str(base) for _, base in prepared)
    if input(f"Organize these {len(prepared)} folders?\n  {listing}\n[y/N] ").strip().lower() not in ("y", "yes"):
        sys.exit("Cancelled.")


def main():
    args = parse_args()
    setup_logging(args.verbose, args.log_file)
    if args.source and args.source.endswith('"'):
        # Windows quirk: -s "D:\" reaches us as  D:"  (backslash + quote); restore the folder
        args.source = args.source.rstrip('"') + "\\"

    if args.init_config:
        out = Path(DEFAULT_CONFIG_NAME)
        if out.exists():
            sys.exit(f"{out} already exists, not overwriting.")
        out.write_text(json.dumps(DEFAULT_CONFIG, indent=2), encoding="utf-8")
        print(f"Wrote {out}. Edit it, then run: python organizer.py -c {out}")
        return

    base_cfg, cfg_path = load_config(args.config)
    if cfg_path:
        log.info("using config: %s", cfg_path)
    if args.set_aside and not args.find_duplicates:
        sys.exit("--set-aside only works together with --find-duplicates.")
    if args.snooze is not None:
        do_snooze(args.snooze)
        return
    if args.resume:
        do_resume()
        return
    if args.doctor or args.status:
        sys.exit(run_doctor(base_cfg, full=args.doctor))
    commands = (args.history or args.restore or args.undo or args.find_duplicates or args.suggest
                or args.space or args.archive_old)
    if args.all and (args.restore or args.undo or args.find_duplicates):
        sys.exit("--all works with organizing, --history and --suggest. "
                 "For undo, restore and duplicates, name one folder with -s.")

    targets = prepare_targets(args, base_cfg)
    if not targets:
        if args.all and args.scheduled and not watch_entries(base_cfg):
            return                                   # nothing is set up to watch: a quiet, successful run
        sys.exit("None of the watched folders exist.")

    if commands:
        for cfg, base in targets:
            if len(targets) > 1:
                print(f"\n=== {base} ===")
            run_command(cfg, base, args)
        return

    prepared = []
    for cfg, base in targets:
        try:
            check_safe(base, cfg["recursive"], args.force)
            prepared.append((cfg, base))
        except SystemExit as exc:
            if not args.all:
                raise
            log.error("skipping %s: %s", base, exc.code)
    if not prepared:
        sys.exit("No folder could be organized.")
    if args.all:
        confirm_all(prepared, args)
    else:
        confirm(prepared[0][1], prepared[0][0], args)

    try:
        while True:
            for cfg, base in prepared:
                try:
                    organize_one(cfg, base, args)
                except Exception as exc:            # one folder failing must not stop the others
                    if not args.all:
                        raise
                    log.error("%s failed: %s", base, exc)
            if not args.watch:
                break
            time.sleep(args.interval)
    except KeyboardInterrupt:
        log.info("stopped")


def _wait_for_enter():
    if sys.stdin is not None and sys.stdin.isatty():
        try:
            input("\nPress Enter to close this window...")
        except EOFError:
            pass


if __name__ == "__main__":
    pause = "--pause" in sys.argv
    try:
        main()
    except SystemExit as exc:
        code = exc.code
        if isinstance(code, str):
            print(code, file=sys.stderr)
            code = 1
        if pause:
            _wait_for_enter()
        sys.exit(code)
    if pause:
        _wait_for_enter()
