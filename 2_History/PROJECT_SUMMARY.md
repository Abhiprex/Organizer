# Organizer - project summary (current version: 2.8)

Use this as the knowledge/instructions document for the Claude Project. It says what the project is,
what exists, how it works, what was tested, what is NOT proven, and what is planned.

## 1. What this is
A Python tool (stdlib only, Windows-first, also runs on macOS/Linux) that keeps messy folders such as
Downloads tidy. It sorts files into folders by type, name and size, can run by itself in the background,
and everything it does can be previewed and undone. It also has a health check, a repair tool, a pause
button, a space report and duplicate detection.

User context: the owner is Abhijeet Patil (embedded-systems student, Windows PC). He has no messy folder
to test with, so testing is done on synthetic folders; the Windows-specific parts have only been tested
in simulation and need a first real run. He prefers short answers when tokens are low, downloadable
files (always a zip plus key files), and low-risk behaviour that needs little experimenting.

## 2. The deliverable
`Organizer_2.8.zip` -> unzip to a permanent folder (e.g. D:\Organizer_2.8). Layout: `1_Project` (program files; run `install.bat` there), `2_History` (CHANGELOG, TEST_RESULTS, this summary), `3_Possible_Updates` (UPDATES_PLAN, TODO).

| File | Purpose |
|---|---|
| organizer.py | the engine (sorting, undo, history, duplicates, folders, --all, suggest, doctor, space, archive) |
| organizer_config.json | settings: rules, sub-folders, topics, watched folders, clean-up, new-type folders |
| manage_folders.py | menu/CLI to add/remove own folders, topics, watched folders, clean-up, suggestions (folders.bat) |
| setup_windows.py | creates/removes the scheduled task and right-click menu (install.bat / uninstall.bat) |
| repair.py | diagnoses and fixes problems, restore/reset settings, support report (repair.bat) |
| install.bat uninstall.bat folders.bat doctor.bat snooze.bat resume.bat space.bat repair.bat | double-click helpers (CRLF line endings) |
| README.txt | user guide (CRLF) |
| TODO.txt | ideas not built yet |
| organizer_app.py | the desktop window + tray icon (app.bat) |
| app_backend.py | all the logic behind the window (no screen needed, fully tested) |
| presets/*.json | 7 ready-made ways of organizing |
| app.bat build_exe.bat | start the app / build dist\Organizer\Organizer.exe |

First steps on the real PC: `install.bat`, then `doctor.bat`; if anything shows [X], run `repair.bat`,
and if still stuck use repair.bat option 5 (support report) and send the report.

## 3. Features by version
- **1.0 core**: organize the folder you run it from (or `-s`); rules by extension/pattern/regex/size, first match
  wins; sub-folders (extension, year, month, year-month, first-letter, size, topic); Documents holds PDF/DOCX/PPTX/
  XLSX/CSV/XML/TXT... each in its own sub-folder; Images/Videos/Audio/Code by type; Build files rule (Makefile,
  CMakeLists.txt...); real-screenshot rule; ignore list (e.g. password exports); skips hidden files, partial
  downloads, files changed in the last 30 s; name clashes renamed "(1)"; `--dry-run`; `--undo`; safety stops
  (system folders always refused; project folders/home need `--force`); confirmation prompt; locks; dated log.
- **2.0**: Windows scheduled task (runs on battery, catches up), right-click menu, topic folders by keyword (RTOS,
  IoT, ARM, RISC-V, Resume), install/uninstall bats, history in `history/`.
- **2.1**: `folders.bat` menu: add/remove own folders for specific files (project README/.bat/.xml/.exe), add files,
  switch folders off/on, "where would this file go" check; config backups (.bak).
- **2.2**: `--history`, `--undo RUN_ID`, `--restore FILE`; `--find-duplicates` (+`--set-aside`); duplicates caught while
  organizing even under different names; right-click Undo / Find duplicates.
- **2.3**: loose FOLDERS are organized (Projects/Photos/Documents/Code by contents; only after 24 h untouched; never
  venv/node_modules; never the Organizer folder); several watched folders (`watch`, `--all`); `--suggest` proposes
  topic/project folders from your own file names; recursive mode keeps code projects whole.
- **2.4**: `--doctor`/`--status` health check; `--snooze`/`--resume` pause (automatic runs only); installer asks run
  interval (5-1440 min); `--space` report; `--archive-old` (installers 30 d, zips 60 d, disk images 30 d ->
  Archive/<year>/<kind>; never deletes; optional automatic once a day).
- **2.5**: `repair.bat`/`repair.py` (see section 6); settings files saved by Notepad (BOM) load; damaged settings give a
  clear "run repair.bat" message in the log.
- **2.6**: files whose type has no rule go to `Other/<EXT>` automatically (setting `unknown_extensions.min_files`,
  default 1); no-extension, odd or Windows-reserved names (CON, NUL...) stay loose in Other.
- **2.7 (stress-test hardening)**: a FILE named like a destination folder no longer breaks that category (uses
  "Documents (folder)"); error flood limiter + stop-early circuit breaker; undo records written after EVERY move so a
  crash/kill/Ctrl+C can still be undone.
- **2.7.1 (test-driven fixes)**: crash lock freed by process check; undo record written BEFORE each move; slow-regex guard; future-dated files organized; long-name clash shortened; odd names safe in the log; vanished files skipped; permission errors worded correctly; damaged history warning; `~$*` ignored; Makefile sorted; many new types + Firmware folder; dotless extensions fixed; rule destinations must stay inside the folder (`allow_outside` to override); read-only Organizer folder stops clearly; undo/--clean-empty remove empty folders; logging never fatal.
- **2.8 (desktop app)**: window with tabs Organize / History / My Rules / Dashboard / Settings; tray icon when `pystray` + `pillow` are installed; presets (Standard, Standard + year folders, Student, Office / Work, Photographer, Embedded engineer, Minimal); per-user data folder (`%APPDATA%\Organizer`: organizer_config.json, history/, app_settings.json) so many users can share one install; export/import settings; start-with-Windows (a .vbs in the Startup folder); optional background tidy timer; `build_exe.bat` (PyInstaller, onedir). Rules in the editor can only point inside the organized folder. One setup for everything: settings and history live in the user's data folder (`%APPDATA%\\Organizer`; override with `ORGANIZER_HOME`; `portable.txt` or `ORGANIZER_PORTABLE=1` = old layout next to the program); the app, command line, folders.bat, repair and the scheduled task all use it. Launcher: `organizer_app.py` (`--selftest`, crash file `startup_error.txt`, one-copy lock `app.lock`) starts `app_window.py`.

## 4. Key settings (organizer_config.json)
source "." (the folder you run from) | recursive false | min_age_seconds 30 | schedule_minutes 30 | subfolders [] |
topics {RTOS, IoT, ARM, RISC-V, Microcontrollers, Resume} | watch [] (paths or {path, overrides}) |
folders {enabled, dest "Folders", min_age_hours 24, skip_if_contains, ignore, unmatched, rules} |
cleanup {enabled false, archive_dest "Archive", rules} | unknown_extensions {enabled true, min_files 1} |
on_conflict rename | dedupe_identical true | duplicates_folder "_Duplicates" | other_folder "Other" |
ignore_patterns (desktop.ini, Thumbs.db, .DS_Store, *.lnk, *password*.csv, user additions) | rules [...].
A rule may have: name, extensions, patterns (globs), regex, min_size_mb/max_size_mb, dest, subfolders, sub_rules,
custom, enabled. Several criteria in one rule are ANDed. Custom rules sit above built-in ones.

## 5. Command reference (organizer.py)
`-s FOLDER`, `-c CONFIG`, `-r`, `-n/--dry-run`, `-y`, `--force`, `--all`, `--watch --interval N`, `--undo [RUN_ID]`,
`--history`, `--restore FILE...`, `--find-duplicates [--set-aside]`, `--suggest [--min-files N]`, `--doctor`, `--status`,
`--snooze DURATION|forever`, `--resume`, `--space`, `--archive-old`, `--subfolders ...`, `--on-conflict`, `--min-age`,
`--clean-empty`, `--pause` (wait for Enter), `--version`. Config lookup: `-c` > organizer_config.json in the current
folder > next to the script. Plain `python organizer.py` = "this folder"; `--all` = every watched folder.

## 6. Architecture and safety principles
- Files are MOVED, never deleted or overwritten (overwrite mode keeps a backup). Every move is recorded.
- History: `history/<folder>_<hash>.jsonl` (undo records, written after every move), `runs.jsonl` (one line per real
  run, used by doctor), `paused.json`, `organizer.log` (rotating, dated), `*.lock` (stale after 15 min),
  `backups/` (repair tool). History lives in the user's data folder (see 2.8), never inside organized folders.
- Moves use a rename; cross-drive uses copy+verify+delete; a locked file is left alone and retried (never half-copied).
- Folders are moved as one unit only when idle 24 h; venvs/node_modules/projects are protected; recursive mode leaves
  projects whole; the Organizer folder itself is never touched.
- Scheduled task = one task running `organizer.py -y --all --scheduled`; paused state affects only scheduled/watch runs.
- repair.py: diagnose -> ask once -> fix, backups first, `--check` strictly read-only (verified), never touches
  organized files; pause and watched-folder removal need an explicit yes; still runs if organizer.py is damaged.
- Version rule: ALL .py files carry "Organizer X.Y" in their first lines; repair.py flags mixed versions, so every
  release must bump every file.

## 7. Testing status
Tested (Linux, synthetic folders; hundreds of scenarios): all sorting rules, undo/restore/history, duplicates,
folder organizing, --all, suggestions, pause, doctor (with simulated task states), archive, repair flows, installer
(simulated registry + Task Scheduler), plus a hostile stress run.
**Stress test (2.7)**: 6,025 files / 86 folders with unicode, emoji, 200-char names, odd characters, 120 unknown
types, 60 identical copies, 40 clashing names, files named like destination folders, links (file, dir, broken, loop),
10-year-future and 1970 dates, 50 empty files, two 512 MB sparse files, a 3,000-file folder, 30-level nesting.
Result after fixes: 0 errors, 0 files lost (6,025 in / 6,025 out), second run moves nothing, ~3 s. 5,000 files:
organize 2.6 s, undo 0.5 s. Crash test: hard kill / Ctrl+C after 150 moves -> all 150 undoable.
**NOT proven (needs real Windows)**: the scheduled-task XML, registry entries/right-click menu, .bat helpers,
file arrival time (st_birthtime) semantics, case-insensitive name clashes, MAX_PATH (260) long paths, Notepad/
PowerShell encodings in practice, Windows 11 "Show more options" menu, behaviour with OneDrive-redirected Downloads.
**Extreme checks not yet run**: files with future dates (they may count as "too new" forever), 255-byte names that
need a "(1)" rename, non-UTF-8 names, permission-denied files/folders, read-only/full destination, 20k+ files for
--suggest/--space/--find-duplicates timing, symlink edge cases in recursive mode, catastrophic regex in a user rule.

**2.7.1 re-test**: 450+ extra tests (simple/medium/hard, incl. random chaos folders, kills, parallel runs, 20k files) all pass or are explained test mistakes; see 2_History/TEST_RESULTS.md. Windows-only items above are STILL not proven.

**2.8 testing**: app_backend.py has 38 automated tests (every preset, rules editor and its error messages, history/undo, two-user isolation, import/export, pause, dashboard). The window code was clicked through with a fake Tkinter (49 checks) because the sandbox has no screen. NOT proven: the real window on Windows (layout, fonts, sizes), the real tray icon, `start with Windows`, and the built .exe.

## 8. Known limitations
Automatic task only runs while the user is logged on. "Old file" ages use modified/arrival time. Moving a project
folder can break things that remember its path (IDE recents) - ignore list or `folders.enabled:false`. Suggestions are
name-based guesses (may suggest the user's own name). Topic matching is by whole words in file names. A generic
README.md can belong to only one custom folder. The desktop app is new and untested on a real screen; the .exe must be built on Windows with build_exe.bat.

## 9. Roadmap / TODO (see TODO.txt)
1. Report-only scan of a whole folder/drive (plan first, nothing moves until approved).
2. Program/game protection (treat app/game folders as one unit; never touch Program Files/Windows/AppData/game libraries).
3. Bat/exe bundles: read a .bat, find the files it needs, keep them together (unsure -> leave and list).
4. Finish the extreme-test list above and fix what it finds.
Other ideas: pause button in right-click menu, notifications after a run, HTML/CSV run reports, sorting by download
source, learning from user corrections, small GUI, single .exe (must be built on Windows).
Open questions for the user: should drive scans ever move files by themselves (suggested: report first); where do
games/programs live; should "one folder per bat" be automatic or approved.

## 10. Working conventions for future sessions
- Build by small patches, test each against synthetic folders, then run the regression suites before packaging.
- Always bump versions in every .py and README, keep .bat/README in CRLF, avoid backslashes in normal docstrings
  (SyntaxWarning), keep ASCII in console output (Windows code pages), pythonw has no stdin (guard `sys.stdin is None`).
- Package as `Organizer_X.Y.zip` (folder `Organizer_X.Y/`), delete the older zip, verify from a clean extraction
  (`organizer.py --version`, `repair.py --check`).
- Never weaken safety to make a test pass; report honestly what was and was not verified.
- Windows gotchas learned: trailing backslash in quoted paths (`-s "D:\"` arrives as `D:"`), schtasks default blocks
  runs on battery (use XML), Notepad adds a BOM (read with utf-8-sig), PowerShell writes UTF-16, reserved device names.
