ORGANIZER 2.1 - quick guide
===========================

SET UP (Windows, once)
  1. Unzip this folder somewhere permanent, e.g. D:\Organizer  (don't move it afterwards).
  2. Double-click install.bat. It shows a PREVIEW of what would happen to your Downloads
     folder first (nothing is moved), then asks two questions:
        - organize Downloads automatically every 30 minutes?
        - add "Organize this folder" to the right-click menu?
     No administrator rights needed.

DAILY USE
  * Automatic: new downloads are sorted within ~30 minutes. Files that changed in the last
    30 seconds are left alone, so downloads in progress are never touched.
  * Right-click a folder (or empty space inside it) > "Organize this folder"
    or "Preview organizing (no changes)". Windows 11: under "Show more options".
  * By hand:   python organizer.py --dry-run     (preview)
               python organizer.py               (organize the folder you are in)
               python organizer.py --undo        (reverse the last run in that folder)

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
