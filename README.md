# Organizer 2.1

Organizer is a Windows-friendly file sorting and directory cleanup tool written in Python. It can sort files in a folder into destinations based on file type, name, topic, or custom rules. The distribution also includes optional Windows batch scripts for setup and folder-rule management.

## Get started

1. Download and extract [`Organizer_2.1.zip`](Organizer_2.1.zip) to a permanent location, such as `D:\Organizer`. Avoid moving the folder after setup.
2. Make sure Python 3 is installed and available on your `PATH`.
3. Run `install.bat` from the extracted folder. It previews the proposed Downloads-folder organization before making changes, then offers optional automatic scheduling and a right-click menu entry. Administrator rights are not required.

The repository also includes `manage_folders.py` and `folders.bat` for managing custom folder rules. The complete application scripts and Windows setup files are included in the ZIP distribution.

## Organize files

From Command Prompt or PowerShell, change to the folder you want to organize and run the script from the extracted Organizer folder:

```bat
python D:\Organizer\organizer.py --dry-run
python D:\Organizer\organizer.py
python D:\Organizer\organizer.py --undo
```

- `--dry-run` previews the proposed moves without changing files.
- Running without an option organizes the current folder.
- `--undo` reverses the most recent organization run for that folder.

You can also right-click a folder, or empty space inside it, and choose **Organize this folder** or **Preview organizing (no changes)**. On Windows 11, these options may appear under **Show more options**.

When automatic organization is enabled, Downloads is checked every 30 minutes. Files changed within the last 30 seconds are skipped so files still downloading are left alone.

## Create custom project folders

Custom rules let you route files for a particular project to one destination before the built-in categories are considered. For example, `README.md`, `build.bat`, `config.xml`, and names containing `tempmonitor` can all be sent to `Projects\TempMonitor`.

Double-click `folders.bat` and select **2) Add a folder for specific files**, or use the command line:

```bat
python manage_folders.py add TempMonitor --files README.md build.bat config.xml tempmonitor
```

By default, the destination is `Projects/TempMonitor` inside the folder being organized. Supply a custom destination with `--dest`:

```bat
python manage_folders.py add TempMonitor --files tempmonitor --types .exe .bat --dest "D:\Projects\TempMonitor"
```

Matching rules:

- Names with a file extension, such as `README.md`, match that exact filename.
- A plain word, such as `tempmonitor`, matches names containing that word.
- Wildcards are supported, such as `setup*.exe`.
- `--types` restricts matches to the listed extensions. When used with `--files`, a file must match both.
- Custom folders are checked before built-in rules. If a custom rule uses only `--types`, all files with those extensions are routed there.

The interactive menu also lets you list folders, add files to an existing rule, remove a rule, turn one off or on, and test where filenames would be routed.

## Configuration and history

- `organizer_config.json` stores your folder rules, topics, and ignore list. It is created from the built-in defaults when needed.
- `organizer_config.json.bak` is a backup made before configuration changes.
- `history/` stores undo history and `organizer.log`, which records runs.
- Topic rules map a folder name to words in filenames. For example, a `RTOS` topic matching `rtos` and `freertos` can sort documents under `Documents/PDF/RTOS`.

Keep your configuration and `history/` folder when upgrading. Organizer does not update itself from the internet; extract a newer version over the old one instead.

## Uninstall

Run `uninstall.bat` from the extracted application folder. Your files, configuration, and history are left in place. If you move the Organizer folder or reinstall Python, run `install.bat` again to refresh the setup.

## License

Organizer is distributed under the [MIT License](LICENSE).
