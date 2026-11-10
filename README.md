# Organizer

![Python](https://img.shields.io/badge/Python-3.x-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Windows](https://img.shields.io/badge/Platform-Windows-0078D6?style=for-the-badge&logo=microsoft&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)

Organizer is a Windows-friendly file sorting and folder cleanup tool that automatically keeps cluttered folders tidy. It is designed for folders such as Downloads, Desktop, and other busy work areas where files tend to accumulate without a clear structure.

The project is built in Python and ships with Windows batch helpers for setup, repair, pause/resume, and folder management. It can organize files by type, apply custom rules, keep project files together, and undo changes with saved history.

## Why this project?

If your Downloads folder is constantly filling up with PDFs, installers, archives, media files, screenshots, source code, and random documents, Organizer helps sort everything into a cleaner layout without needing to do it manually every time.

It supports:

- automatic organization on a schedule
- preview mode before making changes
- right-click folder actions
- custom project folders and subject-based organization
- safe undo and restore support
- health checks, repair tools, and duplicate detection

## Features

- Sorts common file types into sensible destinations
- Leaves active downloads alone for a short grace period
- Supports manual, automatic, and right-click organization
- Handles folders as well as individual files
- Detects duplicate files and can set them aside in `_Duplicates`
- Uses saved history so changes can be reversed
- Includes repair and diagnostics tools when something goes wrong

## Quick start

1. Unzip the project to a permanent location such as `D:\Organizer`.
2. Open the folder and run `install.bat`.
3. Review the preview of how your Downloads folder would be organized.
4. Choose whether to enable automatic sorting and right-click menu entries.

No administrator rights are required.

## Daily use

### Automatic mode

After installation, Organizer can sort new downloads automatically every 30 minutes (or another interval you choose during setup).

Files changed in the last 30 seconds are skipped so downloads in progress are never moved prematurely.

### Right-click usage

Right-click any folder, or empty space inside it, and choose:

- `Organize this folder`
- `Preview organizing (no changes)`

On Windows 11, these options may appear under `Show more options`.

### Command line usage

```bat
python organizer.py --dry-run
python organizer.py
python organizer.py --undo
```

- `--dry-run` previews changes without moving files
- running without flags organizes the current folder
- `--undo` reverses the last organize action for that folder

## New in 2.6: a folder for every new file type

A file whose type has no rule used to land in one large `Other` pile. Now each new type gets its own folder named after the type, created automatically.

Examples:

```text
report.xyz  -> Other\XYZ
game.sav    -> Other\SAV
data.dat    -> Other\DAT
```

The next file of the same type goes into the same folder; a brand-new type creates a new one.

Files with no type (for example `README`, `LICENSE`), odd names like `name.b c`, or names reserved by Windows (`CON`, `NUL`, and similar) stay loose in `Other`.

Everything is undoable with `--undo`, and the behavior appears in `--dry-run` previews.

If you want fewer folders, you can configure:

```json
"unknown_extensions": { "min_files": 3 }
```

This means a folder is created only after 3 files of the same type exist. Smaller piles wait in `Other` and are tidied later.

You can also disable this with:

```json
"unknown_extensions": { "enabled": false }
```

Or via `folders.bat`, or commands such as:

```bat
python manage_folders.py unknown-show
python manage_folders.py unknown-on
python manage_folders.py unknown-off
python manage_folders.py unknown-min 3
```

## Repair and health checks

### Repair tool

Double-click `repair.bat` to run the built-in repair and diagnostics flow.

The menu includes:

1. Check and repair everything (recommended)
2. Only check
3. Restore settings from a backup
4. Reset settings to defaults
5. Save a support report

It can repair common issues such as:

- damaged settings files
- wrong configuration values
- broken automatic task setup
- stale right-click menu entries
- crashed-run leftovers and stale locks
- missing history folders

It can also tell you about:

- missing or damaged program files
- watched folders that are missing
- folders Organizer cannot modify
- Python versions that are too old

It backs up changes before modifying anything and never touches the files you have organized.

### Health check

Double-click `doctor.bat` or run:

```bat
python organizer.py --doctor
```

This prints plain-language diagnostics on whether the setup is healthy, including:

- whether the automatic task is installed and pointing at this folder
- when it last ran on each watched folder
- whether problems occurred recently
- whether watched folders still exist and are writable
- whether disk space is low

## Pause, cleanup, and space reports

### Pause

Double-click `snooze.bat` to pause automatic organization for a chosen period. Use `resume.bat` to end the pause early.

While paused, automatic runs do nothing, but manual organizing still works.

### Space report

Double-click `space.bat`, or run:

```bat
python organizer.py --space -s FOLDER
```

This shows:

- which folders take the most space
- the largest files and their age
- how much room `_Duplicates` is using
- old installers, archives, and disk images that may be worth archiving

Cleanup of old files is also supported:

```bat
python organizer.py --archive-old
```

This moves older installers and archives into `Archive\<year>\<kind>`. Use `--dry-run` to preview and `--undo` to reverse it.

## Everyday problem solvers

### 1) Folders are organized too

Loose folders in Downloads can be classified and moved into folders like:

- `Folders\Projects`
- `Folders\Photos`
- `Folders\Documents`
- `Folders\Code`

This is intentionally conservative:

- only after the folder has remained unchanged for a configured time
- never if it contains a virtual environment or `node_modules`
- never the Organizer folder itself or the folder you are running from
- all moved as one piece, with `--undo` available

You can also turn this off in `organizer_config.json`:

```json
"folders": { "enabled": false }
```

and control unmatched folders with:

```json
"folders": { "unmatched": "Folders/Other" }
```

### 2) Several folders in one go

List watched folders in `organizer_config.json` or via `folders.bat`/`manage_folders.py`.

```bat
python organizer.py --all
```

This organizes every watched folder. The scheduled task installed by `install.bat` does the same, so Downloads, Desktop, and other folders can stay tidy together.

### 3) Suggestions from your own files

```bat
python organizer.py --suggest
```

This inspects your existing file names and suggests folder names such as topics or projects based on recurring words.

Examples:

- a word appearing in 3+ files of one kind becomes a topic
- a word shared by files of multiple types becomes a project

You can apply suggestions with `manage_folders.py` or choose them interactively.

## Undo, history, and duplicates

Every move is recorded so nothing is lost.

```bat
python organizer.py --history
python organizer.py --undo
python organizer.py --undo RUN_ID
python organizer.py --restore "report.pdf"
```

- `--history` lists past runs
- `--undo` reverses the last run
- `--undo RUN_ID` undoes any earlier run without disturbing newer work
- `--restore` restores a single file or wildcard match

Duplicates are also detected:

- identical files are set aside in `_Duplicates`
- `python organizer.py --find-duplicates` reports duplicates without changing anything
- `--set-aside` moves duplicates into `_Duplicates` when approved

## Custom project folders

Organizer supports your own project-specific folders so related files stay together.

Example setup:

```text
name:   TempMonitor
files:  README.md, build.bat, config.xml, tempmonitor
types:  leave empty
where:  press Enter for Projects\TempMonitor
```

This routes matching files to `Projects\TempMonitor` before the built-in rules are checked.

Custom folders can be managed via `folders.bat` or `manage_folders.py`. Their rules are checked before standard organizer rules, so your own layout wins.

## Configuration and history files

Organizer stores its settings and actions in the installed folder:

- `organizer_config.json` — your rules, topics, and ignored items
- `organizer_config.json.bak` — backup created before configuration changes
- `history/` — undo history and organizer logs

Example topic configuration:

```json
"RTOS": ["rtos", "freertos"]
```

This helps route technical documents into groups like `Documents\PDF\RTOS`.

## Updating and reinstalling

Organizer does not update itself from the internet. To upgrade:

1. Download the new version
2. Unzip it over the old folder
3. Keep your existing `organizer_config.json` and `history/` directory

If you move the Organizer folder or reinstall Python, run `install.bat` again.

## Subject folders

In `organizer_config.json`, the `topics` section maps a folder name to words found in file names. For example:

```json
"RTOS": ["rtos", "freertos"]
```

Documents containing those terms can then be routed into folders such as `Documents\PDF\RTOS`.

## Remove Organizer

Double-click `uninstall.bat`.

This removes the Organizer integration without deleting your files, rules, or history.

## Repository layout

```text
.
├── organizer.py
├── manage_folders.py
├── repair.py
├── setup_windows.py
├── organizer_config.json
├── install.bat
├── uninstall.bat
├── folders.bat
├── doctor.bat
├── repair.bat
├── snooze.bat
├── resume.bat
├── space.bat
├── README.md
├── README.txt
├── LICENSE
├── TODO.txt
└── history/
```

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.
