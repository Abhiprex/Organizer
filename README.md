# Organizer

Organizer is a Windows utility that automatically sorts files in your Downloads and other folders into cleaner, more useful destinations. It helps you keep your workspace organized without manually moving files one by one.

Built in Python and designed for everyday Windows use, Organizer can:

- sort new downloads into categories like Documents, PDFs, Installers, Code, and More
- leave files still being downloaded alone until they settle
- organize folders on demand from the right-click menu or CLI
- support custom project folders so related files stay together
- keep undo history so you can roll back recent runs

## Why Organizer?

A cluttered Downloads folder is one of the most common digital headaches. Organizer gives you a repeatable way to keep your files tidy by applying rules automatically and consistently.

Instead of manually sorting everything, you can:

- preview changes before moving files
- set up automatic organization every 30 minutes
- create custom folders for a specific project or file group
- define your own naming and file-type rules

## Features

- Automatic sorting for Windows folders
- Safe preview mode before any changes happen
- Skip logic for files modified recently, so in-progress downloads are protected
- Right-click integration for quick folder organization
- Custom folder rules for project-specific organization
- Undo support with saved history
- Optional topic-based organization rules

## Quick start

1. Download and extract `Organizer_2.1.zip` to a permanent location such as `D:\Organizer`.
2. Open the extracted folder.
3. Double-click `install.bat`.
4. Review the preview of how your Downloads folder would be organized.
5. Choose whether to enable:
   - automatic organization every 30 minutes
   - "Organize this folder" in the right-click menu

No administrator rights are required.

## Daily use

### Automatic organization

After setup, new downloads are sorted approximately every 30 minutes. Files changed in the last 30 seconds are left alone, preventing incomplete downloads from being moved.

### Right-click menu

Right-click a folder or an empty space inside a folder and choose one of the Organizer options:

- Organize this folder
- Preview organizing (no changes)

On Windows 11, these may appear under Show more options.

### Command line

From a terminal, you can run:

```bat
python organizer.py --dry-run
python organizer.py
python organizer.py --undo
```

- `--dry-run` shows what would happen without making any changes
- running without flags organizes the current folder
- `--undo` reverses the last organize action for that folder

## Custom project folders

Organizer 2.1 adds support for your own folders for files that belong to a project or a specific category.

Example: keep all TempMonitor-related files together.

Double-click `folders.bat`, then choose:

- `2) Add a folder for specific files`

When prompted, enter values like:

```text
name:   TempMonitor
files:  README.md, build.bat, config.xml, tempmonitor
types:  leave empty
where:  press Enter for Projects\TempMonitor
```

This causes those files to go only to that folder instead of the standard categories such as PDF, Installers, Code, and so on.

Custom rules are checked before built-in organizer rules, so your own folders win.

### Matching behavior

- names with a dot, such as `README.md`, match that exact file name
- plain words, such as `tempmonitor`, match any file whose name contains that word
- wildcards are supported, for example `setup*.exe`
- `--types` can limit matching to file extensions such as `.exe` or `.bat`
- if both `--files` and `--types` are used, a file must match both conditions

The built-in interactive menu also lets you:

- list all folders
- add more file patterns to an existing rule
- remove a custom folder
- turn a rule on or off
- test where a file would go before running organization

## Configuration and history

Organizer stores its settings and history in the folder where it is installed:

- `organizer_config.json` — your folder rules, topics, and ignore list
- `organizer_config.json.bak` — backup created before configuration changes
- `history/` — undo history and organizer logs

You can define custom topics in the config, for example:

```json
"RTOS": ["rtos", "freertos"]
```

This allows documents to be sorted into subfolders like `Documents\PDF\RTOS`.

## Updating and reinstalling

Organizer does not update itself from the internet. To upgrade:

1. download the new version
2. unzip it over the old folder
3. keep your existing `organizer_config.json` and `history/` folder

If you move the Organizer folder or reinstall Python, run `install.bat` again.

## Remove Organizer

Double-click `uninstall.bat`.

Your files, rules, and history remain in place. Organizing will simply stop being set up on your system until you run the installer again.

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.

## Repository structure

- `organizer.py` — main organizer logic
- `manage_folders.py` — custom folder manager
- `install.bat` — one-time setup for automatic scheduling and context menu
- `uninstall.bat` — remove Organizer integration without deleting your files
- `folders.bat` — quick access to custom project folder management
- `organizer_config.json` — user configuration
- `history/` — undo and log data
