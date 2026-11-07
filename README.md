# Organizer

![Python](https://img.shields.io/badge/Python-3.x-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Windows](https://img.shields.io/badge/Platform-Windows-0078D6?style=for-the-badge&logo=microsoft&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)

Organizer is a Windows-friendly file sorting utility that automatically organizes cluttered folders such as Downloads into cleaner, more useful destinations.

The tool is designed to keep your workspace tidy with minimal effort. It can sort files by type, name, custom rules, and project-specific folders while protecting active downloads from being moved mid-transfer.

## Why this project?

If your Downloads folder keeps filling up with PDFs, installers, archives, code files, screenshots, and random documents, Organizer helps you put everything in the right place without manual sorting.

It supports:

- automatic folder cleanup
- preview mode before making changes
- right-click folder organization
- custom project folders
- file-type and name-based rules
- undo support via saved history

## Features

- Automatic sorting for common file categories
- Safe preview mode before moving files
- Grace period for recently modified files so downloads in progress are not touched
- Right-click integration for fast manual sorting
- Custom rules for project-based organization
- Backup and undo history support
- Built from Python with Windows batch helpers for setup and management

## Quick start

1. Download and extract `Organizer_2.1.zip` to a permanent location such as `D:\Organizer`.
2. Make sure Python 3 is installed and available on your `PATH`.
3. Double-click `install.bat`.
4. Review the preview of how your Downloads folder would be organized.
5. Choose whether to enable automatic sorting and the right-click menu option.

No administrator rights are required.

## Daily use

### Automatic mode

Once installed, Organizer can sort new downloads automatically every 30 minutes.

Files changed in the last 30 seconds are skipped so incomplete downloads are not moved prematurely.

### Right-click usage

Right-click any folder, or empty space inside a folder, and choose:

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

## Custom project folders

Organizer 2.1 supports your own project-specific folders so files that belong together stay together.

Example: keep all files related to a project named `TempMonitor` in one place.

Double-click `folders.bat` and choose:

- `2) Add a folder for specific files`

Then enter values like:

```text
name:   TempMonitor
files:  README.md, build.bat, config.xml, tempmonitor
types:  leave empty
where:  press Enter for Projects\TempMonitor
```

This sends matching files to `Projects\TempMonitor` instead of the default categories such as PDF, Installers, or Code.

Custom folders are checked before built-in organizer rules, so your own rules take priority.

### Matching rules

- file names with a dot such as `README.md` match that exact filename
- plain words such as `tempmonitor` match any filename containing that word
- wildcards are supported, for example `setup*.exe`
- `--types` limits matches to a specific extension like `.exe` or `.bat`
- when used together, `--files` and `--types` must both match

The interactive manager also lets you:

- list your folders
- add more files to an existing folder
- remove a folder
- enable or disable a folder
- test where a file would go before running organization

## Configuration and history

Organizer stores its settings and actions in the installed folder:

- `organizer_config.json` — your rules, topics, and ignore list
- `organizer_config.json.bak` — backup created before configuration changes
- `history/` — undo history and log files

Example topic configuration:

```json
"RTOS": ["rtos", "freertos"]
```

This can help route files such as technical documents into folder groups like `Documents\PDF\RTOS`.

## Updating and reinstalling

Organizer does not update itself from the internet. To upgrade:

1. download the new version
2. unzip it over the old folder
3. keep your existing `organizer_config.json` and `history/` directory

If you move the Organizer folder or reinstall Python, run `install.bat` again.

## Uninstall

Double-click `uninstall.bat`.

This removes the Organizer integration without deleting your files, rules, or history.

## Repository layout

```text
.
├── organizer.py
├── install.bat
├── uninstall.bat
├── folders.bat
├── manage_folders.py
├── organizer_config.json
├── README.md
├── README.txt
├── Organizer_2.1.zip
├── LICENSE
└── history/
```

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.
