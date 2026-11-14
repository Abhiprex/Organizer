# Organizer - possible updates

## 0. Done in 2.8: the desktop app (see CHANGELOG). First thing to do: run app.bat on Windows and send a screenshot or the error text of anything that looks wrong.

### App ideas for next time
- (done in 2.8) one shared history and settings for the app, command line and scheduled task
- Make the shipped default settings generic (the sample topics RTOS / IoT / ARM are the author's own; they live in the 'Embedded engineer' preset)
- Drag a folder onto the window; progress bar with file count; light/dark theme
- Rule wizard ("files from this website", "files bigger than..."), a preview of the folder tree after organizing
- A 'Family / shared PC' setup guide; update check; localized text (Hindi, Marathi)
- Windows notifications after a run; right-click menu entry that opens the app on that folder

## A. Done in 2.7.1 (all 20 test findings fixed, see 2_History/TEST_RESULTS.md)
Bad regex hang, Makefile, 255-char clash, future dates, odd names in the log, vanishing files, permission wording,
damaged-history warning, ~$ temp files, small items (undo id message, empty folders after undo, manage_folders without
keyboard, scheduled run with nothing to watch, dry-run hint, "saved as (1)" log line), new file types + Firmware folder,
dotless extensions, read-only Organizer folder, rule destinations kept inside the folder, crash lock, undo saved before each move.

## B. Decisions for you
1. Rules can now only send files into the organized folder; "allow_outside": true lifts that (never into system folders). OK?
2. Firmware folder holds hex, bin, elf, map, s19, srec, axf, uf2, lst. Want other embedded types (ioc, uvprojx, sch, brd)?
3. .epub goes to Ebooks and .psd/.ai to Design (existing folders). Keep?

## C. Roadmap (from TODO.txt)
1. Report-only scan of a whole folder/drive (plan first, nothing moves until approved)
2. Program/game protection (treat app/game folders as one unit; never touch Program Files/Windows/AppData)
3. Bat/exe bundles: read a .bat, find the files it needs, keep them together (unsure -> leave and list)
4. Real-Windows checks: install.bat, doctor.bat, scheduled task, right-click menu, long paths, OneDrive Downloads, full disk

## D. Other ideas
Pause button in right-click menu, notifications after a run, HTML/CSV run reports, sorting by download source,
learning from your corrections, small GUI, single .exe (must be built on Windows).

## E. Open questions
Should drive scans ever move files by themselves (suggested: report first)? Where do games/programs live?
Should "one folder per bat" be automatic or approved?
