ORGANIZER 2.8 - quick guide
===========================

NEW IN 2.8: THE DESKTOP APP
---------------------------
Double-click app.bat. You get a window with five tabs:
  Organize   pick a folder, press Preview to see what would move, then Organize now (with one-click undo).
  History    every run, the files in it, undo a run or put single files back.
  My Rules   change the sorting rules, topics, ignore list and watched folders; test 'where would this file go?'.
  Dashboard  health check, space report, duplicates, pause / resume, recent runs.
  Settings   choose a way of organizing (Standard, by year, Student, Office, Photographer, Embedded engineer,
             Minimal), options, export / import your settings, start with Windows, background tidying.
Everyone who logs in to the PC gets their own settings and undo history (in %APPDATA%\Organizer), so several
people can use one copy and each organize their own way. Share a setup with a friend via Export / Import.
Tray icon: run  pip install pystray pillow  once. Then closing the window keeps Organizer in the tray; right-click
the icon to organize now, pause, resume or quit. Without those two packages the app works as a normal window.
Want a real .exe? Double-click build_exe.bat (needs internet once). It creates dist\Organizer\Organizer.exe.
ONE SHARED SETUP: the window, the command line, folders.bat and the background task all use the SAME settings
and the SAME undo history, stored in your own folder (%APPDATA%\Organizer). So whatever the background task moves,
the app can undo - and a rule you add in the app is used by the task. Each Windows user has their own.
Old 'everything next to the program' layout (for a USB stick): create an empty file called portable.txt next to organizer.py.
Window does not open? Double-click selftest.bat - it checks Python, Tkinter and your folders and says what to fix.
If the app cannot start it writes the reason to %APPDATA%\Organizer\startup_error.txt instead of just disappearing.
The app has NOT yet been run on a real Windows screen - see 2_History\TEST_RESULTS.md for what was tested.


NEW IN 2.7.1 (fixes found by 300+ extra tests)
----------------------------------------------
- A crash or killed run no longer blocks the next run for 15 minutes.
- Undo records are saved BEFORE each move, so even a hard kill can be undone.
- A rule with a very slow pattern (regex) is switched off instead of freezing the run.
- Files with a future date are organized (they count as 'arrived now').
- Very long names that clash are shortened before adding (1). Odd file names no longer break the log.
- Files that vanish mid-run are skipped, not counted as errors. Permission problems say so.
- Office temp files (~$name.docx) are ignored. Makefile is sorted again.
- More file types sorted (html, css, raw, m4v, mid, go, rs, sql ...) and a new Firmware folder (hex, bin, elf, map).
- Rules written as "pdf" now work like ".pdf". A rule cannot send files outside the folder unless it has
  "allow_outside": true. --clean-empty and undo also remove empty category folders.
- If the Organizer folder is read-only it now stops with a clear message instead of saving history elsewhere.


SET UP (Windows, once)
  1. Unzip this folder somewhere permanent, e.g. D:\Organizer  (don't move it afterwards).
  2. Double-click install.bat. It shows a PREVIEW of what would happen to your Downloads
     folder first (nothing is moved), lets you add more folders to watch (Desktop, a scans
     folder ...), then asks two questions:
        - organize these folders automatically every 30 minutes?
        - add the "Organize this folder" entries to the right-click menu?
     No administrator rights needed.

DAILY USE
  * Automatic: new downloads are sorted within ~30 minutes. Files that changed in the last
    30 seconds are left alone, so downloads in progress are never touched.
  * Right-click a folder (or empty space inside it) > "Organize this folder"
    or "Preview organizing (no changes)". Windows 11: under "Show more options".
  * By hand:   python organizer.py --dry-run     (preview)
               python organizer.py               (organize the folder you are in)
               python organizer.py --undo        (reverse the last run in that folder)

TOUGHENED BY A STRESS TEST (new in 2.7)
  A deliberately hostile test folder (6,000 files: odd names, 120 unknown types, files named
  "Documents" or "Images", links, 3,000-file folders, clock-skewed dates) found three problems,
  now fixed:
    1) A FILE named like a destination folder (a file called "Documents", "Images", "Other" ...)
       used to make every move into that folder fail. Organizer now uses "Documents (folder)".
    2) One root cause could produce thousands of identical errors and keep hammering. It now lists
       the first 20, then stops early if most files are failing (disk full, no permission).
    3) Undo records used to be written only at the END of a run, so a crash, a killed task or
       Ctrl+C left moved files that could not be undone. They are now saved after every move:
       after a hard kill every move that happened can still be undone.
  Nothing was ever lost in the test: 6,025 files in, 6,025 files out.

NEW FILE TYPES GET THEIR OWN FOLDER (new in 2.6)
  A file whose type has no rule used to land in one big "Other" pile. Now each new type gets
  its own folder, named after the type, created automatically:
      report.xyz  -> Other\XYZ        game.sav -> Other\SAV        data.dat -> Other\DAT
  The next file of the same type goes into the same folder; a brand-new type creates a new one.
  Files with no type (README, LICENSE), an odd one ("name.b c") or a name Windows reserves
  (CON, NUL ...) stay loose in Other. Everything is undoable (--undo) and shows in --dry-run.
  Want fewer folders? "unknown_extensions": {"min_files": 3} makes a folder only once 3 files of
  a type exist; smaller piles wait in Other and are tidied into the folder later.
  Turn it off with {"enabled": false}. Easiest: folders.bat, option 13, or
  python manage_folders.py unknown-show / unknown-on / unknown-off / unknown-min 3

SOMETHING NOT WORKING? DOUBLE-CLICK repair.bat   (new in 2.5)
  It checks everything that commonly goes wrong and fixes what it safely can. Menu:
    1) Check and repair everything (recommended) - shows what it found, asks once, fixes, re-checks
    2) Only check - changes absolutely nothing
    3) Restore my settings from a backup - pick from a dated list
    4) Reset settings to the defaults - a backup is kept, so nothing is lost for good
    5) Save a support report - a text file (Organizer-report.txt) to send when asking for help;
       your user name is hidden, but look it over first
  It can repair:
    - a damaged or unreadable settings file (keeps what is still good, else restores a backup)
    - a wrong value in the settings (only that part is reset; your own folders are kept)
    - the automatic task: missing, switched off, pointing at another copy, or Python moved
    - the right-click menu pointing at another copy
    - leftovers of a crashed run: stale locks, damaged history lines, a half-saved settings file
    - a missing history folder
  It can only TELL you about (it cannot create missing program files):
    - missing, damaged or mixed-version program files   -> unzip the newest zip over this folder
      (keep organizer_config.json and the history folder)
    - a watched folder that is missing (it asks before removing it - it may just be a USB drive)
    - folders Organizer is not allowed to change, or a Python older than 3.8
  Safety: everything it changes is backed up first in history\backups; it never touches the files
  you have organized; a pause you set yourself is only cancelled if you say yes; and
  "python repair.py --check" is strictly read-only. If organizer.py itself is damaged, repair
  still runs and tells you which file to replace.
  Why a .bat and not an .exe: it uses the same Python and the files next to it, so it works
  even when the rest is broken. (doctor.bat only LOOKS; repair.bat looks and fixes.)

IS IT WORKING? PAUSE? WHAT TAKES SPACE? (new in 2.4)
  1) HEALTH CHECK - double-click doctor.bat  (or: python organizer.py --doctor)
     Says in plain words whether everything works, with a "fix:" line for anything that does not:
       - is the automatic task installed, switched on, and pointing at THIS folder?
       - when did it last run on each watched folder, and did anything go wrong?
       - are the watched folders there and writable, is there disk space, errors in the last day?
     Lines marked [X] are real problems, [!] are things to look at, [ok] is fine.
     "python organizer.py --status" is the short version.
  2) PAUSE - double-click snooze.bat (asks how long: 30m, 2h, 1d, forever) and resume.bat to undo.
     While paused the AUTOMATIC runs do nothing; organizing you start yourself (right-click menu,
     python organizer.py) still works. A pause ends by itself. Also in folders.bat, option 11.
     HOW OFTEN: install.bat asks how often to run (10, 30 or 60 minutes are good; 5 to 1440 allowed).
     Run install.bat again to change it.
  3) SPACE REPORT - double-click space.bat  (or: python organizer.py --space -s FOLDER)
     Shows what takes room (by folder), the 10 biggest files and how old they are, how much the
     _Duplicates folder holds, and old installers / zips / disk images that could be archived.
     CLEAN-UP of old files never deletes anything: python organizer.py --archive-old moves
     installers older than 30 days, zips older than 60 and disk images older than 30 into
     Archive\<year>\<kind>\ (--dry-run previews, --undo reverses). It only looks at files inside
     your organized Installers / Archives / Disk Images folders - never your project folders.
     An "old" file means it has not changed AND did not arrive recently (a fresh download of an old
     file is not old). Change the days or switch on AUTOMATIC clean-up (once a day) in folders.bat,
     option 12, or:  python manage_folders.py cleanup-on / cleanup-set Installers 14

EVERYDAY PROBLEM SOLVERS (new in 2.3)
  1) FOLDERS ARE ORGANIZED TOO, not just files.
     A loose folder in Downloads (an unzipped project, a photo dump, a pile of PDFs) moves to
     Folders\Projects, Folders\Photos, Folders\Documents, Folders\Code ... based on what is
     inside it. It is deliberately careful:
       - only when NOTHING inside has changed for 24 hours (change with "min_age_hours")
       - never a folder holding a venv or node_modules (moving those breaks them)
       - never the Organizer folder, or the folder you are running from
       - the whole folder moves as one piece and "--undo" puts it back
       - recursive mode (-r) also leaves code projects and venvs whole instead of scattering them
     Heads-up: moving a project can break things that remember its old location (an IDE's
     recent list, a build cache). If that matters to you, add the folder's name to
     "folders": {"ignore": ["MyProject"]}  or turn the feature off with
     "folders": {"enabled": false}  in organizer_config.json.
     "folders": {"unmatched": "Folders/Other"} sweeps every other loose folder too.
  2) SEVERAL FOLDERS IN ONE GO.
     List them under "watch" (folders.bat, option 8, or: python manage_folders.py watch-add PATH).
     python organizer.py --all organizes every watched folder; the scheduled task from
     install.bat does exactly that, so Downloads, Desktop and a scans folder all stay tidy.
     One folder having a problem (missing, or refused by the safety check) never stops the others.
     An entry can carry its own settings, e.g.
       "watch": ["C:/Users/you/Downloads", {"path": "C:/Users/you/Desktop", "other_folder": null}]
     Plain "python organizer.py" (without --all) still means "the folder I am in".
  3) SUGGESTIONS FROM YOUR OWN FILES.
     python organizer.py --suggest          (or folders.bat, option 7)
     looks at the file names you already have and proposes folders:
       - a word in 3+ names, all one kind of file  -> a SUBJECT (e.g. "WhatsApp videos")
       - a word shared by files of several types   -> a PROJECT (e.g. "tempmonitor": .exe .xml .bat)
     Words that already have a folder are not repeated. Nothing changes until you choose; the
     menu applies your picks, or:  python manage_folders.py suggest --apply 1 3
     Subject topics can also be managed by hand: topic-add / topic-list / topic-remove.

UNDO, HISTORY AND DUPLICATES (new in 2.2)
  Every move is recorded, so nothing is ever lost:
    python organizer.py --history                list every run (id, time, number of files)
    python organizer.py --undo                   undo the last run
    python organizer.py --undo RUN_ID            undo ANY earlier run (newer runs stay as they are)
    python organizer.py --restore "report.pdf"   put back just one file (wildcards ok: "n*.txt")
  Because Organizer can run by itself every 30 minutes, "the last run" is often tiny -
  use --history to find the run you want.
  Duplicates:
    * While organizing, a file whose CONTENT is identical to one already in its destination
      folder - even under another name, like "report (1).pdf" - is set aside in _Duplicates.
    * python organizer.py --find-duplicates      reports identical files ANYWHERE in the folder
      (nothing is changed). It marks which copy it would keep (the one not named like a copy,
      nearest the top, shortest name, oldest).
    * add --set-aside to move the extra copies into _Duplicates (asks first; undoable with --undo).
    Delete the _Duplicates folder yourself once you have looked inside.
  The right-click menu also has "Undo last organizing" and "Find duplicate files".
  After updating from an older version, run install.bat once more (it switches the automatic
  task to the newest mode, lets you pick how often it runs, and keeps your settings).

MY OWN FOLDERS (new in 2.1) - e.g. keep one project's files together
  Double-click folders.bat, choose "2) Add a folder for specific files", and answer:
    name:   TempMonitor
    files:  README.md, build.bat, config.xml, tempmonitor
            (names with a dot are matched exactly; a plain word like "tempmonitor" matches
             every file with that word in its name, whatever the type)
    types:  leave empty (or limit it, e.g. .exe .bat - then a file must match BOTH)
    where:  press Enter for Projects\TempMonitor, or give a full path like D:\Projects\TempMonitor
  From then on those files go ONLY there - not to PDF, Installers, Code etc.
  Your folders are checked first, so they win over the built-in ones.
  Menu option 6 shows where any file name would go, before you run anything.
  Other options: add more files, remove a folder, or switch one off/on.
  Tip: generic names like README.md can belong to only one project at a time, so for
  several projects use a word from the project's own name wherever possible.
  Every change saves a backup: organizer_config.json.bak

UPDATING
  Organizer does not update itself from the internet (that would mean running downloaded
  code). To upgrade, unzip the new version over the old folder: keep your
  organizer_config.json (your folders and rules) and the history\ folder.

WHERE THINGS ARE
  organizer_config.json   your rules (your folders, topics, ignore list)
  history\                undo history + organizer.log (dated record of every run)

SUBJECT FOLDERS
  In organizer_config.json, "topics" maps a folder name to words in file names, e.g.
  "RTOS": ["rtos", "freertos"]. Documents then sort as Documents\PDF\RTOS. Add your own.

REMOVE
  Double-click uninstall.bat. Your files, rules and history are left as they are.
  If you move the Organizer folder or reinstall Python, run install.bat again.
