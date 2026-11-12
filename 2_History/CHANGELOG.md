# Organizer - update history (what changed in each version)

| Version | What was added |
|---|---|
| 1.0 | Core sorting by type/name/size, sub-folders, Documents folder with per-type sub-folders, ignore list, dry-run, undo, safety stops, log |
| 2.0 | Windows scheduled task (runs on battery), right-click menu, topic folders (RTOS, IoT, ARM, RISC-V, Resume), install/uninstall bats |
| 2.1 | folders.bat menu: own folders for specific files, switch folders off/on, "where would this file go" check, config backups |
| 2.2 | --history, --undo RUN_ID, --restore FILE, duplicate detection (+ set aside), right-click Undo / Find duplicates |
| 2.3 | Loose FOLDERS organized, several watched folders (--all), --suggest, recursive mode keeps projects whole |
| 2.4 | --doctor/--status, pause (--snooze/--resume), run interval choice, --space report, --archive-old |
| 2.5 | repair.bat / repair.py, Notepad (BOM) settings load, clear message for damaged settings |
| 2.6 | Unknown file types go to Other/<EXT> automatically; odd and reserved Windows names stay loose |
| 2.7 | Stress-test hardening: file named like a destination folder, error-flood limiter, undo records saved after EVERY move |
| 2.7.1 | Fixes for 20 problems found by 450+ extra tests: crash lock freed, undo saved BEFORE each move, slow-regex guard, future dates, long-name clashes, odd file names in the log, vanished files, permission messages, damaged history warning, ~$ temp files, Makefile, many new file types + Firmware folder, rules without a dot, rule destinations kept inside the folder, read-only Organizer folder message, undo/--clean-empty tidy empty folders, logging never fatal |

Rule for every release: bump the version in ALL .py files and the README, keep .bat and README in CRLF,
run the regression + test suites, package as Organizer_X.Y.zip.
