#!/usr/bin/env python3
"""
Organizer 2.1 - manage your own folders (no JSON editing needed)

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

How files are matched
  --files   a name with a dot (README.md, build.bat) matches that exact file name;
            a plain word (tempmonitor) matches any file whose name contains it;
            wildcards work too (setup*.exe)
  --types   limit to file types (.exe .bat .xml). Combined with --files, a file must match both.
            With --types only, EVERY file of those types goes to the folder.

Your folders are checked BEFORE the built-in ones, so they win. A backup of the config
(organizer_config.json.bak) is saved before every change.
"""

import argparse
import json
import re
import shutil
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
DEFAULT_CONFIG = HERE / "organizer_config.json"
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
        return json.loads(path.read_text(encoding="utf-8"))
    except ValueError as exc:
        sys.exit(f"{path} is not valid JSON ({exc}). Nothing was changed.")


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
# Interactive menu
# --------------------------------------------------------------------------- #
def split_input(text):
    return [part.strip() for part in text.split(",") if part.strip()]


def pick_name(cfg, prompt):
    custom = [r["name"] for r in cfg["rules"] if r.get("custom")]
    if custom:
        print("  Your folders: " + ", ".join(custom))
    return input(prompt).strip()


def menu(cfg, path):
    print("\n=== Organizer 2.1 - my folders ===")
    print(f"Settings file: {path}")
    while True:
        print("""
 1) Show all folders
 2) Add a folder for specific files (e.g. a project)
 3) Add more files to one of my folders
 4) Remove a folder
 5) Turn a folder off / on
 6) Check where a file would go
 0) Exit""")
        choice = input("Choose: ").strip()
        try:
            if choice == "0" or choice == "":
                return
            if choice == "1":
                print("\n" + action_list(cfg))
            elif choice == "2":
                name = input("\nName of the folder (e.g. TempMonitor): ").strip()
                print("Which files belong to it? Type file names or words, separated by commas.")
                print("  Names with a dot are exact (README.md, build.bat); plain words match any")
                print("  file with that word in its name (tempmonitor).")
                names = split_input(input("> "))
                types = input("Only certain file types? (optional, e.g. .exe .bat .xml - Enter = any)\n  A file must match a name AND be one of these types: ").split()
                default = f"Projects/{name}"
                dest = input(f"Where should they go? [{default}]\n  (inside the organized folder, or a full path like D:\\Projects\\{name or 'App'}): ").strip()
                print()
                trial = json.loads(json.dumps(cfg))
                message = action_add(trial, name, names, types, dest)
                print(message)
                if input("\nSave this? [Y/n] ").strip().lower() in ("", "y", "yes"):
                    cfg.clear()
                    cfg.update(trial)
                    save(cfg, path)
                    print("Saved. Try option 6 to check where your files would go.")
                else:
                    print("Nothing saved.")
            elif choice == "3":
                name = pick_name(cfg, "\nWhich folder? ")
                names = split_input(input("File names or words to add (comma separated): "))
                types = input("File types to add (optional, e.g. .exe .xml): ").split()
                print(action_add_files(cfg, name, names, types))
                save(cfg, path)
                print("Saved.")
            elif choice == "4":
                name = pick_name(cfg, "\nFolder to remove: ")
                if input(f'Remove "{name}"? Files already moved stay where they are. [y/N] ').strip().lower() in ("y", "yes"):
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
                names = split_input(input("\nFile names to check (comma separated, e.g. README.md, setup.exe): "))
                if names:
                    print(action_test(cfg, names))
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
    parser.add_argument("-c", "--config", help="config file (default: organizer_config.json next to this script)")
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
