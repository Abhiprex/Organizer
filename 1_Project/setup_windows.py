#!/usr/bin/env python3
"""
Organizer 2.7.1 - Windows helper for organizer.py  (use install.bat / uninstall.bat, or run it directly)

  python setup_windows.py install     preview, then optionally:
                                        1) organize your watched folders (Downloads, Desktop, ...)
                                           automatically every 30 minutes (one Task Scheduler task)
                                        2) add "Organize this folder" to the right-click menu
  python setup_windows.py uninstall   remove both (your files and history are not touched)
  python setup_windows.py status      show what is installed

Options for install:  --folder PATH   folder to watch (repeat it for several; default: Downloads)
                      --every N       minutes between automatic runs (default 30; asked if not given)
                      --no-auto       skip the automatic schedule
                      --no-menu       skip the right-click menu
                      --yes           do not ask questions

No administrator rights are needed: everything is created for the current user only.
Nothing moves files except organizer.py itself, and the preview shows what it would do first.
"""

import argparse
import os
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from xml.sax.saxutils import escape

HERE = Path(__file__).resolve().parent
ORGANIZER = HERE / "organizer.py"
TASK_NAME = "FolderOrganizer"
INTERVAL_MINUTES = 30

MENU_BASE = r"Software\Classes\Directory"
# (registry path under HKEY_CURRENT_USER, menu text, path placeholder, extra arguments)
#   %1 = the folder you right-clicked, %V = the folder you are inside (right-click on empty space)
MENU_ENTRIES = [
    (MENU_BASE + r"\shell\FolderOrganizer", "Organize this folder", "%1", []),
    (MENU_BASE + r"\Background\shell\FolderOrganizer", "Organize this folder", "%V", []),
    (MENU_BASE + r"\shell\FolderOrganizerPreview", "Preview organizing (no changes)", "%1", ["--dry-run"]),
    (MENU_BASE + r"\Background\shell\FolderOrganizerPreview", "Preview organizing (no changes)", "%V", ["--dry-run"]),
    (MENU_BASE + r"\shell\FolderOrganizerUndo", "Undo last organizing", "%1", ["--undo"]),
    (MENU_BASE + r"\Background\shell\FolderOrganizerUndo", "Undo last organizing", "%V", ["--undo"]),
    (MENU_BASE + r"\shell\FolderOrganizerDupes", "Find duplicate files (changes nothing)", "%1", ["--find-duplicates"]),
    (MENU_BASE + r"\Background\shell\FolderOrganizerDupes", "Find duplicate files (changes nothing)", "%V", ["--find-duplicates"]),
]


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def is_windows():
    return sys.platform.startswith("win")


def python_exe(windowless=False):
    """Full path of the Python running this setup (pythonw.exe = no console window)."""
    exe = Path(sys.executable)
    if windowless:
        pythonw = exe.with_name("pythonw.exe")
        if pythonw.exists():
            return pythonw
    return exe


def quoted_folder(folder):
    """A folder path that stays intact inside "quotes" (a trailing backslash would eat the quote)."""
    folder = str(folder)
    return folder + "." if folder.endswith("\\") else folder


def downloads_folder():
    """The real Downloads folder (works even if OneDrive moved it)."""
    if is_windows():
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                                r"Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders") as key:
                value, _ = winreg.QueryValueEx(key, "{374DE290-123F-4565-9164-39C4925E467B}")
                return Path(os.path.expandvars(value))
        except OSError:
            pass
    return Path.home() / "Downloads"


def ask(question, default_yes=True, assume_yes=False):
    if assume_yes:
        return True
    answer = input(f"{question} [{'Y/n' if default_yes else 'y/N'}] ").strip().lower()
    return default_yes if not answer else answer in ("y", "yes")


def run(cmd):
    return subprocess.run(cmd, capture_output=True, text=True)


# --------------------------------------------------------------------------- #
# Scheduled task
# --------------------------------------------------------------------------- #
def task_arguments():
    return f'"{ORGANIZER}" -y --all --scheduled'


def task_xml(minutes=INTERVAL_MINUTES):
    """Task Scheduler definition. Unlike the plain schtasks command line, this lets the task
    run on battery power and catch up after the PC was off."""
    start = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    return f"""<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.2" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <RegistrationInfo>
    <Description>Organizes the folders listed under "watch" in organizer_config.json</Description>
  </RegistrationInfo>
  <Triggers>
    <TimeTrigger>
      <Repetition>
        <Interval>PT{minutes}M</Interval>
        <StopAtDurationEnd>false</StopAtDurationEnd>
      </Repetition>
      <StartBoundary>{start}</StartBoundary>
      <Enabled>true</Enabled>
    </TimeTrigger>
  </Triggers>
  <Principals>
    <Principal id="Author">
      <LogonType>InteractiveToken</LogonType>
      <RunLevel>LeastPrivilege</RunLevel>
    </Principal>
  </Principals>
  <Settings>
    <MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>
    <DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>
    <StopIfGoingOnBatteries>false</StopIfGoingOnBatteries>
    <StartWhenAvailable>true</StartWhenAvailable>
    <AllowStartOnDemand>true</AllowStartOnDemand>
    <Enabled>true</Enabled>
    <ExecutionTimeLimit>PT30M</ExecutionTimeLimit>
  </Settings>
  <Actions Context="Author">
    <Exec>
      <Command>{escape(str(python_exe(windowless=True)))}</Command>
      <Arguments>{escape(task_arguments())}</Arguments>
      <WorkingDirectory>{escape(str(HERE))}</WorkingDirectory>
    </Exec>
  </Actions>
</Task>
"""


def task_exists():
    return run(["schtasks", "/Query", "/TN", TASK_NAME]).returncode == 0


def create_task(minutes=INTERVAL_MINUTES):
    """Returns (ok, message)."""
    xml_file = Path(tempfile.gettempdir()) / "folder_organizer_task.xml"
    xml_file.write_text(task_xml(minutes), encoding="utf-16")
    try:
        result = run(["schtasks", "/Create", "/TN", TASK_NAME, "/XML", str(xml_file), "/F"])
    finally:
        try:
            xml_file.unlink()
        except OSError:
            pass
    if result.returncode == 0:
        return True, "scheduled (runs even on battery, catches up after the PC was off)"

    # Fallback: plain command line (works everywhere, but Windows may skip runs on battery power)
    command = f'"{python_exe(windowless=True)}" {task_arguments()}'
    result = run(["schtasks", "/Create", "/TN", TASK_NAME, "/SC", "MINUTE", "/MO", str(minutes),
                  "/TR", command, "/F"])
    if result.returncode == 0:
        return True, "scheduled (basic mode: Windows may pause it while on battery power)"
    return False, (result.stderr or result.stdout).strip()


def delete_task():
    if not task_exists():
        return False
    return run(["schtasks", "/Delete", "/TN", TASK_NAME, "/F"]).returncode == 0


# --------------------------------------------------------------------------- #
# Right-click menu
# --------------------------------------------------------------------------- #
def menu_command(placeholder, extra):
    # The folder goes LAST: if it ends in a backslash (a drive root like D:\) Windows glues
    # the closing quote onto it, and organizer.py repairs exactly that case.
    options = " ".join(extra + ["--pause"])
    return f'"{python_exe()}" "{ORGANIZER}" {options} -s "{placeholder}"'


def add_menu():
    import winreg
    for path, label, placeholder, extra in MENU_ENTRIES:
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, path) as key:
            winreg.SetValueEx(key, "", 0, winreg.REG_SZ, label)
            winreg.SetValueEx(key, "Icon", 0, winreg.REG_SZ, "shell32.dll,-4")
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, path + r"\command") as key:
            winreg.SetValueEx(key, "", 0, winreg.REG_SZ, menu_command(placeholder, extra))


def remove_menu():
    import winreg
    removed = False
    for path, *_ in MENU_ENTRIES:
        for sub in (path + r"\command", path):
            try:
                winreg.DeleteKey(winreg.HKEY_CURRENT_USER, sub)
                removed = True
            except FileNotFoundError:
                pass
    return removed


def menu_installed():
    import winreg
    try:
        winreg.CloseKey(winreg.OpenKey(winreg.HKEY_CURRENT_USER, MENU_ENTRIES[0][0]))
        return True
    except OSError:
        return False


# --------------------------------------------------------------------------- #
# Commands
# --------------------------------------------------------------------------- #
def preview(folder):
    print(f"\nPreview for {folder} (nothing is moved):\n")
    subprocess.run([str(python_exe()), str(ORGANIZER), "--dry-run", "-s", str(folder)])
    print()


def load_manager():
    """manage_folders.py edits organizer_config.json (the watched-folder list lives there)."""
    sys.path.insert(0, str(HERE))
    import manage_folders
    return manage_folders


def choose_minutes(args, config):
    """How often the task runs: --every N, else ask (Enter keeps the current / default value)."""
    current = config.get("schedule_minutes", INTERVAL_MINUTES)
    current = current if isinstance(current, int) and 5 <= current <= 1440 else INTERVAL_MINUTES
    if args.every is not None:
        return args.every
    if args.yes:
        return current
    while True:
        answer = input(f"How often should it organize? Minutes between runs - 10, 30 or 60 are good "
                       f"[{current}]: ").strip()
        if not answer:
            return current
        if answer.isdigit() and 5 <= int(answer) <= 1440:
            return int(answer)
        print("  Please type a whole number of minutes between 5 and 1440.")


def cmd_install(args):
    if not ORGANIZER.exists():
        print(f"organizer.py must be in the same folder as this file ({HERE}).")
        return 1
    if args.every is not None and not 5 <= args.every <= 1440:
        print("--every must be between 5 and 1440 minutes.")
        return 1
    folders = [Path(f).expanduser() for f in (args.folder or [])] or [downloads_folder()]
    for folder in folders:
        if not folder.is_dir():
            print(f"Folder not found: {folder}")
            return 1
    manager = load_manager()
    config = manager.load(manager.DEFAULT_CONFIG)
    minutes = choose_minutes(args, config) if not args.no_auto else INTERVAL_MINUTES

    if not args.no_auto:
        already = manager.watch_paths(config)
        if already:
            print("Already watched: " + ", ".join(already))
        if not args.yes:                      # offer more folders (Desktop, Documents, a scans folder ...)
            while True:
                extra = input("Add another folder to organize automatically? Type its path, e.g. "
                              "C:\\Users\\you\\Desktop  (Enter = no more): ").strip().strip('"')
                if not extra:
                    break
                extra_path = Path(extra).expanduser()
                if extra_path.is_dir():
                    folders.append(extra_path)
                else:
                    print(f"  not found: {extra_path}")
        print("\nFolders to organize automatically:")
        for folder in folders:
            print(f"  {folder}")
        for folder in folders:
            preview(folder)

    done = []
    if not args.no_auto and ask(f"Organize these folders automatically every {minutes} minutes?",
                                True, args.yes):
        changed = False
        for folder in folders:
            try:
                manager.action_watch_add(config, str(folder))
                changed = True
            except ValueError:
                pass                          # already in the list
        if config.get("schedule_minutes") != minutes:
            config["schedule_minutes"] = minutes      # --doctor uses this to spot a stalled schedule
            changed = True
        if changed:
            manager.save(config, manager.DEFAULT_CONFIG)
        ok, message = create_task(minutes)
        print(("  OK: " if ok else "  FAILED: ") + message)
        if ok:
            done.append("automatic organizing")
            print("  Watched folders: " + ", ".join(manager.watch_paths(config)))
    if not args.no_menu and ask('Add "Organize this folder" to the right-click menu?', True, args.yes):
        try:
            add_menu()
            print("  OK: right-click menu added")
            done.append("right-click menu")
        except OSError as exc:
            print(f"  FAILED: {exc}")

    if done:
        print("\nInstalled: " + " and ".join(done) + ".")
        print("Add or remove watched folders any time with folders.bat (option 8).")
        print("Is it working?  doctor.bat      Something wrong?  repair.bat")
        print("Pause for a while:  snooze.bat      Back on:  resume.bat")
        print("Remove everything later with uninstall.bat. Undo a run with:  python organizer.py --history / --undo")
        print("If you move or rename the Organizer folder, or update Python, run install.bat again.")
        if "right-click menu" in done:
            print("On Windows 11 the right-click entries are under 'Show more options'.")
    else:
        print("\nNothing was installed.")
    return 0


def cmd_uninstall(args):
    task = delete_task()
    menu = remove_menu()
    print("Automatic organizing: " + ("removed" if task else "was not installed"))
    print("Right-click menu:     " + ("removed" if menu else "was not installed"))
    print("Your files, settings and history were not touched.")
    return 0


def cmd_status(args):
    print("Automatic organizing: " + ("installed" if task_exists() else "not installed"))
    print("Right-click menu:     " + ("installed" if menu_installed() else "not installed"))
    manager = load_manager()
    config = manager.load(manager.DEFAULT_CONFIG)
    print("Watched folders:      " + (", ".join(manager.watch_paths(config)) or "(none)"))
    print(f"Runs every:           {config.get('schedule_minutes', INTERVAL_MINUTES)} minutes")
    print("For a full check:     doctor.bat")
    return 0


def main():
    parser = argparse.ArgumentParser(description="Set up organizer.py on Windows.")
    sub = parser.add_subparsers(dest="command", required=True)
    install = sub.add_parser("install")
    install.add_argument("--folder", action="append", help="folder to watch (repeat for several)")
    install.add_argument("--no-auto", action="store_true")
    install.add_argument("--no-menu", action="store_true")
    install.add_argument("--yes", action="store_true")
    install.add_argument("--every", type=int, metavar="MINUTES", help="minutes between automatic runs")
    sub.add_parser("uninstall")
    sub.add_parser("status")
    args = parser.parse_args()

    if not is_windows():
        print("This helper is for Windows only (it uses Task Scheduler and the Windows registry).")
        return 1
    return {"install": cmd_install, "uninstall": cmd_uninstall, "status": cmd_status}[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
