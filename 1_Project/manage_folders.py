#!/usr/bin/env python3
"""
Organizer 2.8 - manage your folders, topics, watched folders and clean-up (no JSON editing needed)

Use it to send SPECIFIC files (for example everything that belongs to one project: its
README, .bat, .xml and .exe files) to a folder of your choice, instead of the common
PDF / Installers / Code folders.

  python manage_folders.py                      menu (easiest - or double-click folders.bat)
  python manage_folders.py list                 show all folders
  python manage_folders.py add TempMonitor --files README.md build.bat config.xml tempmonitor
  python manage_folders.py add TempMonitor --files tempmonitor --types .exe .bat --dest "D:\\Projects\\TempMonitor"
  python manage_folders.py add-files TempMonitor --files notes.txt
  python manage_folders.py remove TempMonitor
  python manage_folders.py off TempMonitor      (and  on TempMonitor)  switch a folder off/on
  python manage_folders.py test README.md app.exe   where would these files go?

  python manage_folders.py suggest                 propose folders from the file names you already have
  python manage_folders.py suggest --apply 1 3     ...and create suggestions number 1 and 3
  python manage_folders.py topic-add RTOS --words rtos freertos     subject folders (Documents/PDF/RTOS)
  python manage_folders.py topic-list / topic-remove RTOS
  python manage_folders.py watch-add "C:\\Users\\you\\Desktop"   organize this folder automatically too
  python manage_folders.py watch-list / watch-remove PATH

  python manage_folders.py cleanup-show              old-file clean-up settings
  python manage_folders.py cleanup-on / cleanup-off  archive old installers/zips automatically (once a day)
  python manage_folders.py cleanup-set Installers 14 archive installers older than 14 days
  (health check, pause and the space report are in the menu: options 10, 11 and 12)

  python manage_folders.py unknown-show              automatic folders for new file types
  python manage_folders.py unknown-on / unknown-off  (a file with no rule goes to Other/<TYPE>)
  python manage_folders.py unknown-min 3             only make a folder once 3 such files exist

How files are matched
  --files   a name with a dot (README.md, build.bat) matches that exact file name;
            a plain word (tempmonitor) matches any file whose name contains it;
            wildcards work too (setup*.exe)
  --types   limit to file types (.exe .bat .xml). Combined with --files, a file must match both.
            With --types only, EVERY file of those types goes to the folder.

Your folders are checked BEFORE the built-in ones, so they win. A backup of the config
(organizer_config.json.bak) is saved before every change.
"""

import builtins


def _safe_input(prompt=""):
    """input() that ends quietly when there is no keyboard (double-click without a console, piped input)."""
    try:
        return builtins.input(prompt)
    except (EOFError, RuntimeError):
        print()
        raise SystemExit(0)


import argparse
import json
import re
import shutil
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent


def _default_config():
    """The settings file in use (per-user, shared with the app and the scheduled task)."""
    try:
        sys.path.insert(0, str(HERE))
        import organizer
        return organizer.ensure_user_config()
    except Exception:
        return HERE / "organizer_config.json"


DEFAULT_CONFIG = _default_config()
BAD_NAME_CHARS = set('\\/:*?"<>|')
BAD_PATH_CHARS = set('*?"<>|')


# --------------------------------------------------------------------------- #
# Config file
# --------------------------------------------------------------------------- #
def load(path):
    if not path.exists():
        sys.path.insert(0, str(HERE))
        import organizer                                  # first use: start from the built-in defaults
        cfg = json.loads(json.dumps(organizer.DEFAULT_CONFIG))
        path.write_text(json.dumps(cfg, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"(created {path.name} with the default folders)")
        return cfg
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))     # -sig: tolerate Notepad's hidden BOM
    except ValueError as exc:
        sys.exit(f"{path} is not valid JSON ({exc}). Nothing was changed.\n"
                 "Double-click repair.bat to restore it from a backup.")


def save(cfg, path):
    if path.exists():
        shutil.copy2(path, path.with_name(path.name + ".bak"))
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(cfg, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.replace(path)                                      # never leaves a half-written config


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def find_rule(cfg, name):
    for index, rule in enumerate(cfg["rules"]):
        if rule.get("name", "").lower() == name.strip().lower():
            return index, rule
    return None, None


def parse_names(items):
    """File names / words -> patterns. Returns (patterns, error or None)."""
    patterns = []
    for raw in items:
        item = raw.strip()
        if not item:
            continue
        if "*" in item or "?" in item:
            pattern = item
        elif re.search(r"\.[A-Za-z0-9]{1,6}$", item):
            pattern = item                                  # exact file name, e.g. README.md
        else:
            if len(item) < 3:
                return None, f'"{item}" is too short to use as a word (it would match too many files).'
            pattern = f"*{item}*"                           # a word inside the name
        if pattern.replace("*", "").replace(".", "").strip() == "":
            return None, f'"{item}" would match every file.'
        if pattern not in patterns:
            patterns.append(pattern)
    return patterns, None


def parse_types(items):
    types = []
    for raw in items:
        for part in re.split(r"[,\s]+", raw.strip()):
            if not part:
                continue
            ext = "." + part.lstrip(".").lower()
            if ext == "." or not re.fullmatch(r"\.[a-z0-9]{1,10}", ext):
                return None, f'"{part}" is not a file type (use something like .exe or .xml).'
            if ext not in types:
                types.append(ext)
    return types, None


def safe_dest(name, dest):
    """Default destination is Projects/<name>. Relative paths live inside the organized folder;
    full paths (D:\\Projects\\App) are used as they are."""
    dest = (dest or f"Projects/{name}").strip().strip('"')
    parts = Path(dest).parts
    body = parts[1:] if Path(dest).anchor else parts
    if not body:
        return None, "Please give a folder name, not just a drive."
    if any(set(part) & BAD_PATH_CHARS or part in (".", "..") for part in body):
        return None, f'"{dest}" contains characters Windows does not allow in folder names.'
    return dest, None


def describe(rule):
    bits = []
    if "patterns" in rule:
        bits.append("names: " + ", ".join(rule["patterns"]))
    if "extensions" in rule:
        bits.append("types: " + " ".join(rule["extensions"]))
    if "patterns" in rule and "extensions" in rule:
        bits = [" AND ".join(bits)]                         # both must match
    if "regex" in rule:
        bits.append(f'regex: {rule["regex"]}')
    if "min_size_mb" in rule or "max_size_mb" in rule:
        bits.append("by size")
    return "; ".join(bits) or "(no matching conditions)"


# --------------------------------------------------------------------------- #
# Actions (each returns a message; raises ValueError for user mistakes)
# --------------------------------------------------------------------------- #
def action_list(cfg):
    lines = []
    for index, rule in enumerate(cfg["rules"], 1):
        tags = ("  [yours]" if rule.get("custom") else "") + ("  [OFF]" if rule.get("enabled", True) is False else "")
        lines.append(f"{index:>2}. {rule.get('name')}{tags}\n      -> {rule.get('dest')}\n      {describe(rule)}")
    return "\n".join(lines)


def action_add(cfg, name, names, types, dest):
    name = (name or "").strip()
    if not name or len(name) > 60 or set(name) & BAD_NAME_CHARS:
        raise ValueError('Give the folder a short name without these characters:  \\ / : * ? " < > |')
    if find_rule(cfg, name)[1] is not None:
        raise ValueError(f'A folder called "{name}" already exists. Use add-files to add more files to it.')
    patterns, error = parse_names(names or [])
    if error:
        raise ValueError(error)
    ext_list, error = parse_types(types or [])
    if error:
        raise ValueError(error)
    if not patterns and not ext_list:
        raise ValueError("Say which files belong in it: file names/words (--files) and/or file types (--types).")
    dest, error = safe_dest(name, dest)
    if error:
        raise ValueError(error)

    rule = {"name": name, "custom": True}
    if patterns:
        rule["patterns"] = patterns
    if ext_list:
        rule["extensions"] = ext_list
    rule["dest"] = dest
    position = 0                                            # after your earlier folders, before the built-in ones
    while position < len(cfg["rules"]) and cfg["rules"][position].get("custom"):
        position += 1
    cfg["rules"].insert(position, rule)
    note = ""
    if not patterns:
        note = f"\n  Note: ALL {' '.join(ext_list)} files will now go to this folder, not to the usual ones."
    return f'Added "{name}" -> {dest}\n  {describe(rule)}{note}'


def action_add_files(cfg, name, names, types):
    _, rule = find_rule(cfg, name)
    if rule is None:
        raise ValueError(f'No folder called "{name}". Use "list" to see the names.')
    patterns, error = parse_names(names or [])
    if error:
        raise ValueError(error)
    ext_list, error = parse_types(types or [])
    if error:
        raise ValueError(error)
    if not patterns and not ext_list:
        raise ValueError("Say what to add: file names/words (--files) and/or file types (--types).")
    for pattern in patterns:
        if pattern not in rule.setdefault("patterns", []):
            rule["patterns"].append(pattern)
    for ext in ext_list:
        if ext not in rule.setdefault("extensions", []):
            rule["extensions"].append(ext)
    return f'Updated "{rule["name"]}"\n  {describe(rule)}'


def action_remove(cfg, name):
    index, rule = find_rule(cfg, name)
    if rule is None:
        raise ValueError(f'No folder called "{name}". Use "list" to see the names.')
    del cfg["rules"][index]
    extra = "" if rule.get("custom") else "\n  (That was one of the built-in folders: its files now fall into the 'Other' folder.)"
    return f'Removed "{rule["name"]}". Files already moved stay where they are.{extra}'


def action_toggle(cfg, name, enabled):
    _, rule = find_rule(cfg, name)
    if rule is None:
        raise ValueError(f'No folder called "{name}". Use "list" to see the names.')
    if enabled:
        rule.pop("enabled", None)
    else:
        rule["enabled"] = False
    return f'"{rule["name"]}" is now {"ON" if enabled else "OFF"}.'


def action_test(cfg, names):
    sys.path.insert(0, str(HERE))
    import organizer
    lines = []
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        for name in names:
            path = base / name
            path.write_text("")
            dest, label = organizer.pick_destination(cfg, base, path, 0)
            if dest is None:
                where = "(left where it is)"
            else:
                try:
                    where = str(dest.relative_to(base)) or "."
                except ValueError:
                    where = str(dest)
            lines.append(f"  {name}  ->  {where}   [{label or '-'}]")
    return "\n".join(lines) + "\n  (files that are brand new are left alone for the first 30 seconds)"


# --------------------------------------------------------------------------- #
# Topics, watched folders, suggestions
# --------------------------------------------------------------------------- #
def norm_path(text):
    return str(Path(text.strip().strip('"')).expanduser())


def watch_paths(cfg):
    return [w if isinstance(w, str) else w.get("path", "") for w in cfg.get("watch", [])]


def same_folder(a, b):
    try:
        return Path(a).expanduser().resolve() == Path(b).expanduser().resolve()
    except OSError:
        return str(a).lower() == str(b).lower()


def action_watch_list(cfg):
    paths = watch_paths(cfg)
    if not paths:
        return "No folders are watched yet. Add one with:  watch-add PATH"
    return "\n".join(f"{i:>2}. {path}{'' if Path(path).expanduser().is_dir() else '   (not found!)'}"
                     for i, path in enumerate(paths, 1))


def action_watch_add(cfg, path):
    folder = Path(norm_path(path))
    if not folder.is_dir():
        raise ValueError(f"Folder not found: {folder}")
    if any(same_folder(folder, existing) for existing in watch_paths(cfg)):
        raise ValueError(f"{folder} is already watched.")
    cfg.setdefault("watch", []).append(str(folder))
    return (f"Now watching {folder}\n  It is organized when you run organizer.py --all "
            f"(the scheduled task from install.bat does exactly that).")


def action_watch_remove(cfg, path):
    entries = cfg.get("watch", [])
    for index, existing in enumerate(watch_paths(cfg)):
        if same_folder(existing, norm_path(path)) or existing.lower() == path.strip().lower():
            del entries[index]
            return f"No longer watching {existing}. Files already organized stay where they are."
    raise ValueError(f'"{path}" is not in the watched list. Use watch-list to see the folders.')


def clean_words(words):
    cleaned = []
    for raw in words:
        word = re.sub(r"\s+", " ", raw.strip().lower())
        if len(re.sub(r"[^a-z0-9]", "", word)) < 2:
            raise ValueError(f'"{raw}" is too short to be a useful word.')
        if word not in cleaned:
            cleaned.append(word)
    return cleaned


def action_topic_list(cfg):
    topics = cfg.get("topics", {})
    if not topics:
        return "No subject topics yet. Add one with:  topic-add NAME --words word1 word2"
    using = [r["name"] for r in cfg["rules"]
             if "topic" in (r.get("subfolders", cfg.get("subfolders", [])) or [])]
    lines = [f"{name}: {', '.join(words)}" for name, words in topics.items()]
    lines.append(f"\nSubject folders are used inside: {', '.join(using) if using else '(no folder yet - use --in)'}")
    return "\n".join(lines)


def action_topic_add(cfg, name, words, in_rules=None):
    name = (name or "").strip()
    if not name or len(name) > 40 or set(name) & BAD_NAME_CHARS:
        raise ValueError('Give the topic a short name without these characters:  \\ / : * ? " < > |')
    words = clean_words(words or [])
    if not words:
        raise ValueError("Give at least one word that appears in the file names (--words).")
    topics = cfg.setdefault("topics", {})
    existing = next((k for k in topics if k.lower() == name.lower()), None)
    if existing:
        merged = topics[existing] + [w for w in words if w not in topics[existing]]
        topics[existing] = merged
        message = f'Updated topic "{existing}": {", ".join(merged)}'
    else:
        topics[name] = words
        message = f'Added topic "{name}": {", ".join(words)}'
    enabled = []
    for rule_name in in_rules or []:
        _, rule = find_rule(cfg, rule_name)
        if rule is None:
            raise ValueError(f'No folder called "{rule_name}" to put subject folders in. Use "list" to see names.')
        modes = list(rule.get("subfolders", cfg.get("subfolders", [])) or [])
        if "topic" not in modes:
            rule["subfolders"] = modes + ["topic"]
            enabled.append(rule["name"])
    if enabled:
        message += f"\n  Subject folders are now also used inside: {', '.join(enabled)}"
    if not any("topic" in (r.get("subfolders", cfg.get("subfolders", [])) or []) for r in cfg["rules"]):
        message += "\n  Note: no folder uses subject folders yet. Add  --in Documents  to turn them on."
    return message


def action_topic_remove(cfg, name):
    topics = cfg.get("topics", {})
    match = next((k for k in topics if k.lower() == name.strip().lower()), None)
    if match is None:
        raise ValueError(f'No topic called "{name}". Use topic-list to see them.')
    del topics[match]
    return f'Removed topic "{match}". Files already moved stay where they are.'


def default_suggest_folder(cfg):
    paths = watch_paths(cfg)
    if paths:
        return paths[0]
    downloads = Path.home() / "Downloads"
    return str(downloads if downloads.is_dir() else Path.cwd())


def get_suggestions(cfg, folder, min_files):
    sys.path.insert(0, str(HERE))
    import organizer
    base = Path(norm_path(folder)).resolve()
    if not base.is_dir():
        raise ValueError(f"Folder not found: {base}")
    suggestions, scanned = organizer.suggest_groups(cfg, base, min_files)
    return organizer, suggestions, scanned, base


def apply_suggestion(cfg, item):
    if item["kind"] == "project":
        return action_add(cfg, item["name"], [item["word"]], [], None)
    return action_topic_add(cfg, item["name"], [item["word"]], item["needs_topic"])


# --------------------------------------------------------------------------- #
# Clean-up settings
# --------------------------------------------------------------------------- #
def load_organizer():
    sys.path.insert(0, str(HERE))
    import organizer
    return organizer


def materialize_cleanup(cfg):
    """Make sure the config holds a full "cleanup" block (older configs only have the defaults implicitly)."""
    organizer = load_organizer()
    block = json.loads(json.dumps(organizer.cleanup_cfg(cfg)))
    cfg["cleanup"] = block
    return block


def action_cleanup_show(cfg):
    block = load_organizer().cleanup_cfg(cfg)
    lines = [("Clean-up is ON: old files are archived automatically (at most once a day)"
              if block["enabled"] else "Clean-up is OFF (use --archive-old, or the menu, to run it by hand)")
             + f"\n  archive folder: {block['archive_dest']}/<year>/<rule>/   (files are moved, never deleted)"]
    for rule in block["rules"]:
        state = "   [rule OFF]" if rule.get("enabled", True) is False else ""
        lines.append(f"  {rule['name']}: files in the '{rule['folder_rule']}' folder older than "
                     f"{rule['older_than_days']} days{state}")
    return "\n".join(lines)


def action_cleanup_toggle(cfg, on):
    materialize_cleanup(cfg)["enabled"] = bool(on)
    return ("Clean-up is now ON: old files are archived automatically, at most once a day. "
            "Undo with --undo." if on else "Clean-up is now OFF.")


def action_cleanup_set(cfg, name, days):
    try:
        days = int(days)
    except (TypeError, ValueError):
        raise ValueError("Days must be a whole number, e.g. 30.")
    if not 1 <= days <= 3650:
        raise ValueError("Choose between 1 and 3650 days.")
    block = materialize_cleanup(cfg)
    for rule in block["rules"]:
        if rule["name"].lower() == name.strip().lower():
            rule["older_than_days"] = days
            return f'"{rule["name"]}": files older than {days} days are archived.'
    names = ", ".join(r["name"] for r in block["rules"])
    raise ValueError(f'No clean-up rule called "{name}". Rules: {names}')


# --------------------------------------------------------------------------- #
# New file types
# --------------------------------------------------------------------------- #
def action_unknown_show(cfg):
    settings = load_organizer().unknown_cfg(cfg)
    state = "ON" if settings["enabled"] else "OFF"
    rule = ("a folder is made for every new type right away" if settings["min_files"] <= 1 else
            f"a type gets its own folder once {settings['min_files']} such files exist "
            "(smaller piles wait loose in Other and are tidied in later)")
    return (f"New file types: {state}\n  A file whose type has no rule goes to Other/<TYPE>, e.g. Other/DAT.\n"
            f"  Right now: {rule}.\n  Files without a type, or with an odd one (CON, NUL ...), stay in Other.")


def action_unknown_toggle(cfg, on):
    organizer = load_organizer()
    cfg["unknown_extensions"] = json.loads(json.dumps(organizer.unknown_cfg(cfg)))
    cfg["unknown_extensions"]["enabled"] = bool(on)
    return ("New file types now get their own folder (Other/<TYPE>)." if on
            else "New file types now all go into the one Other folder.")


def action_unknown_min(cfg, number):
    try:
        number = int(number)
    except (TypeError, ValueError):
        raise ValueError("Give a whole number, e.g. 1 or 3.")
    if not 1 <= number <= 1000:
        raise ValueError("Choose a number from 1 to 1000.")
    organizer = load_organizer()
    cfg["unknown_extensions"] = json.loads(json.dumps(organizer.unknown_cfg(cfg)))
    cfg["unknown_extensions"]["min_files"] = number
    return ("Every new file type gets a folder right away." if number == 1
            else f"A new file type gets a folder once {number} files of it exist.")


# --------------------------------------------------------------------------- #
# Interactive menu
# --------------------------------------------------------------------------- #
def split_input(text):
    return [part.strip() for part in text.split(",") if part.strip()]


def pick_name(cfg, prompt):
    custom = [r["name"] for r in cfg["rules"] if r.get("custom")]
    if custom:
        print("  Your folders: " + ", ".join(custom))
    return _safe_input(prompt).strip()


def parse_numbers(text, count):
    text = text.strip().lower()
    if text in ("all", "a"):
        return list(range(1, count + 1))
    numbers = []
    for part in re.split(r"[,\s]+", text):
        if part.isdigit() and 1 <= int(part) <= count and int(part) not in numbers:
            numbers.append(int(part))
    return numbers


def menu_suggest(cfg, path):
    folder = _safe_input(f"\nWhich folder should I look at? [{default_suggest_folder(cfg)}]\n> ").strip() or default_suggest_folder(cfg)
    organizer, suggestions, scanned, base = get_suggestions(cfg, folder, 3)
    print()
    organizer.print_suggestions(suggestions, scanned, base, 3)
    if not suggestions:
        return
    chosen = parse_numbers(_safe_input("\nCreate which ones? (e.g. 1,3 or all - Enter = none): "), len(suggestions))
    for number in chosen:
        try:
            print(f"\n[{number}] " + apply_suggestion(cfg, suggestions[number - 1]))
        except ValueError as exc:
            print(f"\n[{number}] skipped: {exc}")
    if chosen:
        save(cfg, path)
        print("\nSaved. Option 6 shows where a file would go.")


def menu_watch(cfg, path):
    print("\nWatched folders (organized automatically):\n" + action_watch_list(cfg))
    choice = _safe_input("\n a) add a folder   r) remove a folder   Enter) back: ").strip().lower()
    if choice == "a":
        print(action_watch_add(cfg, _safe_input("Folder path (e.g. C:\\Users\\you\\Desktop): ")))
        save(cfg, path)
        print("Saved. Run install.bat again if automatic organizing is not set up yet.")
    elif choice == "r":
        print(action_watch_remove(cfg, _safe_input("Folder path to stop watching: ")))
        save(cfg, path)
        print("Saved.")


def menu_topics(cfg, path):
    print("\nSubject topics:\n" + action_topic_list(cfg))
    choice = _safe_input("\n a) add / extend a topic   r) remove a topic   Enter) back: ").strip().lower()
    if choice == "a":
        name = _safe_input("Topic name (e.g. RTOS): ").strip()
        words = split_input(_safe_input("Words that appear in the file names (comma separated): "))
        where = split_input(_safe_input("Use subject folders inside which folders? (e.g. Documents - Enter = leave as is): "))
        print(action_topic_add(cfg, name, words, where))
        save(cfg, path)
        print("Saved.")
    elif choice == "r":
        print(action_topic_remove(cfg, _safe_input("Topic to remove: ")))
        save(cfg, path)
        print("Saved.")


def pick_folder(cfg, question="Which folder?"):
    default = default_suggest_folder(cfg)
    answer = _safe_input(f"\n{question} [{default}]\n> ").strip()
    base = Path(norm_path(answer or default))
    if not base.is_dir():
        raise ValueError(f"Folder not found: {base}")
    return base.resolve()


def merged_config(path):
    """The settings with every missing key filled in, exactly as organizer.py sees them."""
    organizer = load_organizer()
    merged, _ = organizer.load_config(str(path))
    return organizer, merged


def menu_health(cfg, path):
    organizer, merged = merged_config(path)
    print()
    organizer.run_doctor(merged, full=True)


def menu_pause(cfg, path):
    organizer = load_organizer()
    pause = organizer.get_pause()
    print("\nAutomatic organizing is " + (f"PAUSED {organizer.describe_pause(pause)}." if pause else "running normally."))
    print("(Organizing you start yourself always works.)")
    answer = _safe_input("Pause for how long? e.g. 30m, 2h, 1d, forever   (r = resume, Enter = back): ").strip()
    if not answer:
        return
    if answer.lower() in ("r", "resume"):
        organizer.do_resume()
        return
    until = organizer.set_pause(organizer.parse_duration(answer))
    print("Paused " + organizer.describe_pause("forever" if until is None else until) + ".")


def menu_space(cfg, path):
    organizer, merged = merged_config(path)
    while True:
        print("""
 s) Space report (what takes room, what could be archived)
 c) Show clean-up settings
 o) Turn automatic clean-up on / off
 d) Change how old a kind of file must be
 a) Archive old files now (preview first)
 Enter) back""")
        choice = _safe_input("Choose: ").strip().lower()
        if not choice:
            return
        if choice == "s":
            base = pick_folder(cfg)
            print()
            organizer.space_report(merged, base)
        elif choice == "c":
            print("\n" + action_cleanup_show(cfg))
        elif choice == "o":
            on = organizer.cleanup_cfg(merged)["enabled"] is False
            print(action_cleanup_toggle(cfg, on))
            save(cfg, path)
            organizer, merged = merged_config(path)
            print("Saved.")
        elif choice == "d":
            print("\n" + action_cleanup_show(cfg))
            name = _safe_input("\nWhich rule (e.g. Installers)? ").strip()
            days = _safe_input("Archive files older than how many days? ").strip()
            print(action_cleanup_set(cfg, name, days))
            save(cfg, path)
            organizer, merged = merged_config(path)
            print("Saved.")
        elif choice == "a":
            base = pick_folder(cfg)
            print()
            if organizer.archive_old(merged, base, dry_run=True) and \
                    _safe_input("\nMove these files into the Archive folder now? [y/N] ").strip().lower() in ("y", "yes"):
                organizer.archive_old(merged, base, assume_yes=True)
        else:
            print("Please choose one of the letters shown.")


def menu_unknown(cfg, path):
    print("\n" + action_unknown_show(cfg))
    choice = _safe_input("\n o) turn on / off   m) change the minimum number of files   Enter) back: ").strip().lower()
    if choice == "o":
        on = load_organizer().unknown_cfg(cfg)["enabled"] is False
        print(action_unknown_toggle(cfg, on))
        save(cfg, path)
        print("Saved.")
    elif choice == "m":
        print(action_unknown_min(cfg, _safe_input("Make a folder once this many files of a type exist (1 = always): ")))
        save(cfg, path)
        print("Saved.")


def menu(cfg, path):
    print("\n=== Organizer 2.8 - my folders ===")
    print(f"Settings file: {path}")
    while True:
        print("""
 1) Show all folders
 2) Add a folder for specific files (e.g. a project)
 3) Add more files to one of my folders
 4) Remove a folder
 5) Turn a folder off / on
 6) Check where a file would go
 7) Suggest folders from my own files
 8) Watched folders (organized automatically)
 9) Subject topics (RTOS, IoT, ...)
10) Is it working? (health check)
11) Pause / resume automatic organizing
12) Space report and clean-up of old files
13) New file types (automatic folders)
 0) Exit""")
        choice = _safe_input("Choose: ").strip()
        try:
            if choice == "0" or choice == "":
                return
            if choice == "1":
                print("\n" + action_list(cfg))
            elif choice == "2":
                name = _safe_input("\nName of the folder (e.g. TempMonitor): ").strip()
                print("Which files belong to it? Type file names or words, separated by commas.")
                print("  Names with a dot are exact (README.md, build.bat); plain words match any")
                print("  file with that word in its name (tempmonitor).")
                names = split_input(_safe_input("> "))
                types = _safe_input("Only certain file types? (optional, e.g. .exe .bat .xml - Enter = any)\n  A file must match a name AND be one of these types: ").split()
                default = f"Projects/{name}"
                dest = _safe_input(f"Where should they go? [{default}]\n  (inside the organized folder, or a full path like D:\\Projects\\{name or 'App'}): ").strip()
                print()
                trial = json.loads(json.dumps(cfg))
                message = action_add(trial, name, names, types, dest)
                print(message)
                if _safe_input("\nSave this? [Y/n] ").strip().lower() in ("", "y", "yes"):
                    cfg.clear()
                    cfg.update(trial)
                    save(cfg, path)
                    print("Saved. Try option 6 to check where your files would go.")
                else:
                    print("Nothing saved.")
            elif choice == "3":
                name = pick_name(cfg, "\nWhich folder? ")
                names = split_input(_safe_input("File names or words to add (comma separated): "))
                types = _safe_input("File types to add (optional, e.g. .exe .xml): ").split()
                print(action_add_files(cfg, name, names, types))
                save(cfg, path)
                print("Saved.")
            elif choice == "4":
                name = pick_name(cfg, "\nFolder to remove: ")
                if _safe_input(f'Remove "{name}"? Files already moved stay where they are. [y/N] ').strip().lower() in ("y", "yes"):
                    print(action_remove(cfg, name))
                    save(cfg, path)
                    print("Saved.")
            elif choice == "5":
                name = pick_name(cfg, "\nFolder to switch: ")
                _, rule = find_rule(cfg, name)
                if rule is None:
                    raise ValueError(f'No folder called "{name}".')
                print(action_toggle(cfg, name, rule.get("enabled", True) is False))
                save(cfg, path)
                print("Saved.")
            elif choice == "6":
                names = split_input(_safe_input("\nFile names to check (comma separated, e.g. README.md, setup.exe): "))
                if names:
                    print(action_test(cfg, names))
            elif choice == "7":
                menu_suggest(cfg, path)
            elif choice == "8":
                menu_watch(cfg, path)
            elif choice == "9":
                menu_topics(cfg, path)
            elif choice == "10":
                menu_health(cfg, path)
            elif choice == "11":
                menu_pause(cfg, path)
            elif choice == "12":
                menu_space(cfg, path)
            elif choice == "13":
                menu_unknown(cfg, path)
            else:
                print("Please type a number from the menu.")
        except ValueError as exc:
            print(f"\n  Not saved: {exc}")
        except (EOFError, KeyboardInterrupt):
            return


# --------------------------------------------------------------------------- #
# Command line
# --------------------------------------------------------------------------- #
def main():
    parser = argparse.ArgumentParser(description="Manage your own Organizer folders.")
    parser.add_argument("-c", "--config", help="config file (default: your own settings file, shared with the app)")
    sub = parser.add_subparsers(dest="command")
    sub.add_parser("list")
    add = sub.add_parser("add")
    add.add_argument("name")
    add.add_argument("--files", nargs="+", default=[])
    add.add_argument("--types", nargs="+", default=[])
    add.add_argument("--dest")
    more = sub.add_parser("add-files")
    more.add_argument("name")
    more.add_argument("--files", nargs="+", default=[])
    more.add_argument("--types", nargs="+", default=[])
    for command in ("remove", "on", "off"):
        sub.add_parser(command).add_argument("name")
    test = sub.add_parser("test")
    test.add_argument("files", nargs="+")
    sub.add_parser("watch-list")
    for command in ("watch-add", "watch-remove"):
        sub.add_parser(command).add_argument("path")
    sub.add_parser("unknown-show")
    sub.add_parser("unknown-on")
    sub.add_parser("unknown-off")
    sub.add_parser("unknown-min").add_argument("number")
    sub.add_parser("cleanup-show")
    sub.add_parser("cleanup-on")
    sub.add_parser("cleanup-off")
    cleanup_set = sub.add_parser("cleanup-set")
    cleanup_set.add_argument("name")
    cleanup_set.add_argument("days")
    sub.add_parser("topic-list")
    topic = sub.add_parser("topic-add")
    topic.add_argument("name")
    topic.add_argument("--words", nargs="+", required=True)
    topic.add_argument("--in", dest="in_rules", nargs="+", default=[], metavar="FOLDER",
                       help="folders (e.g. Documents Videos) that should use subject folders")
    sub.add_parser("topic-remove").add_argument("name")
    suggest = sub.add_parser("suggest")
    suggest.add_argument("--folder")
    suggest.add_argument("--min-files", type=int, default=3)
    suggest.add_argument("--apply", nargs="+", type=int, metavar="N")
    args = parser.parse_args()

    path = Path(args.config).expanduser() if args.config else DEFAULT_CONFIG
    cfg = load(path)

    if not args.command:
        menu(cfg, path)
        return 0
    try:
        changed = True
        if args.command == "list":
            print(action_list(cfg))
            changed = False
        elif args.command == "test":
            print(action_test(cfg, args.files))
            changed = False
        elif args.command == "unknown-show":
            print(action_unknown_show(cfg))
            changed = False
        elif args.command in ("unknown-on", "unknown-off"):
            print(action_unknown_toggle(cfg, args.command == "unknown-on"))
        elif args.command == "unknown-min":
            print(action_unknown_min(cfg, args.number))
        elif args.command == "cleanup-show":
            print(action_cleanup_show(cfg))
            changed = False
        elif args.command in ("cleanup-on", "cleanup-off"):
            print(action_cleanup_toggle(cfg, args.command == "cleanup-on"))
        elif args.command == "cleanup-set":
            print(action_cleanup_set(cfg, args.name, args.days))
        elif args.command == "watch-list":
            print(action_watch_list(cfg))
            changed = False
        elif args.command == "topic-list":
            print(action_topic_list(cfg))
            changed = False
        elif args.command == "suggest":
            organizer, suggestions, scanned, base = get_suggestions(
                cfg, args.folder or default_suggest_folder(cfg), args.min_files)
            organizer.print_suggestions(suggestions, scanned, base, args.min_files)
            changed = False
            if args.apply:
                for number in args.apply:
                    if not 1 <= number <= len(suggestions):
                        raise ValueError(f"There is no suggestion number {number}.")
                for number in args.apply:
                    print(f"\n[{number}] " + apply_suggestion(cfg, suggestions[number - 1]))
                changed = True
        elif args.command == "watch-add":
            print(action_watch_add(cfg, args.path))
        elif args.command == "watch-remove":
            print(action_watch_remove(cfg, args.path))
        elif args.command == "topic-add":
            print(action_topic_add(cfg, args.name, args.words, args.in_rules))
        elif args.command == "topic-remove":
            print(action_topic_remove(cfg, args.name))
        elif args.command == "add":
            print(action_add(cfg, args.name, args.files, args.types, args.dest))
        elif args.command == "add-files":
            print(action_add_files(cfg, args.name, args.files, args.types))
        elif args.command == "remove":
            print(action_remove(cfg, args.name))
        else:
            print(action_toggle(cfg, args.name, args.command == "on"))
        if changed:
            save(cfg, path)
            print("Saved.")
    except ValueError as exc:
        print(f"Not saved: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
