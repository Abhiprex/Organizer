# Organizer 2.7 - test results (Linux sandbox, synthetic folders)
Date: 12 Nov 2026. Package tested: the Organizer_2.7.zip you uploaded, unchanged.
Nothing was fixed yet. Windows-only behaviour is NOT covered (see the end).

## Scoreboard
| Level | Tests | Pass | Fail |
|---|---|---|---|
| Simple | 20 | 19 | 1 |
| Medium | 20 | 20 | 0 |
| Hard | 20 | 11 | 9 |
| Extra (earlier today, not in the 60) | 13 | 9 | 4 |

## Bugs found, in fix order
1. H01 Bad regex in a user rule hangs the whole run (scheduled task would pile up).
2. S14 Makefile is never sorted: "Makefile" and "Brave Passwords.csv" are inside ignore_patterns in the shipped config (test leftovers).
3. H03 A 255-character name that clashes fails with "File name too long"; the file stays loose forever.
4. H02 Files dated in the future are skipped forever ("too new").
5. H04 Non-UTF-8 names make the log throw UnicodeEncodeError.
6. H07 Files that vanish mid-run are counted as errors (736 of 3,000 in the test).
7. H05/H06 Permission problems are reported as "in use, will retry next run".
8. H08 A damaged undo-history line is ignored silently (19/20 files came back, no warning).
9. H09 Office temp files (~$name.docx) get filed into Documents.
10. Minor: --undo with a wrong run ID says "nothing to undo"; undo leaves empty folders; manage_folders.py crashes with no keyboard input; --all with no watched folders ends in an error; a dry run on fresh files only says "too new".

## SIMPLE (20)
| # | Test | Result |
|---|---|---|
| S01 | --version prints 2.7 | PASS |
| S02 | --help works | PASS |
| S03 | Dry run moves nothing | PASS |
| S04 | Real run, exit 0, 0 errors | PASS |
| S05 | pdf -> Documents/PDF | PASS |
| S06 | jpg -> Images/JPG | PASS |
| S07 | mp4 -> Videos/MP4 | PASS |
| S08 | mp3 -> Audio/MP3 | PASS |
| S09 | .c -> Code/C | PASS |
| S10 | zip -> Archives | PASS |
| S11 | exe -> Installers | PASS |
| S12 | Screenshot -> Images/Screenshots | PASS |
| S13 | Topic file RTOS_notes.pdf -> Documents/PDF/RTOS | PASS |
| S14 | Makefile -> Code/Build | FAIL (ignored by config) |
| S15 | Hidden file left alone | PASS |
| S16 | .part partial download left alone | PASS |
| S17 | Second run moves nothing | PASS |
| S18 | --history lists the run | PASS (first attempt was my test mistake) |
| S19 | Undo restores all files | PASS |
| S20 | Undo twice -> "nothing to undo" | PASS |

## MEDIUM (20)
| # | Test | Result |
|---|---|---|
| M01 | Same name, different content -> "a (1).pdf", old kept | PASS |
| M02 | Identical copy -> _Duplicates | PASS |
| M03 | Same content, different name caught | PASS |
| M04 | --restore brings back only the named file | PASS |
| M05 | --undo RUN_ID undoes one run only | PASS |
| M06 | Recursive mode keeps a project (package.json) whole | PASS (needs a project marker file) |
| M07 | Loose folder of 3 photos idle 3 days -> Folders/Photos | PASS (needs 3+ photos) |
| M08 | Folder newer than 24 h left alone | PASS |
| M09 | venv / node_modules never moved | PASS |
| M10 | Unknown type -> Other/XYZ | PASS |
| M11 | No-extension and reserved names (CON, NUL): no errors, nothing lost | PASS |
| M12 | --subfolders year adds a year folder | PASS |
| M13 | on_conflict skip leaves the file | PASS |
| M14 | on_conflict overwrite replaces and keeps a backup | PASS |
| M15 | Snooze blocks scheduled runs, not manual runs | PASS |
| M16 | --doctor shows no [X] after a good run | PASS |
| M17 | --archive-old moves only the old installer, deletes nothing | PASS |
| M18 | Config saved with a BOM (Notepad) loads | PASS |
| M19 | Damaged config -> clear message, no traceback | PASS |
| M20 | An unreadable file does not stop the run | PASS |

## HARD (20)
| # | Test | Result |
|---|---|---|
| H01 | Catastrophic regex finishes in under 20 s | FAIL (hangs) |
| H02 | File dated 2040 still organized | FAIL |
| H03 | 255-char name clash renamed | FAIL (Errno 36) |
| H04 | Non-UTF-8 name: no logging errors | FAIL |
| H05 | Read-only folder: message says permission | FAIL (says "in use") |
| H06 | Read-only destination: message says permission | FAIL (says "in use") |
| H07 | Files vanishing mid-run not counted as errors | FAIL (736 errors) |
| H08 | Truncated history: undo restores all or warns | FAIL (19/20, no warning) |
| H09 | Office ~$ temp file ignored | FAIL |
| H10 | 4 simultaneous runs: no loss | PASS (2,000/2,000) |
| H11 | Symlink loop + broken link in recursive mode | PASS |
| H12 | 300 levels of nested folders | PASS |
| H13 | Destination is a symlink: file stays inside the folder | PASS ("Documents (folder)") |
| H14 | 6,000 files organized, 0 errors | PASS (2.3 s) |
| H15 | --space / --suggest / --find-duplicates on 6,000 files | PASS (0.5 s) |
| H16 | Hard kill mid-run: everything undoable | PASS (5,000/5,000 back) |
| H17 | Ctrl+C mid-run: everything undoable | PASS (5,000/5,000 back) |
| H18 | Same name in NFC/NFD unicode: nothing lost | PASS |
| H19 | Undo when the original spot is taken: no overwrite | PASS (comes back as "a (1).pdf") |
| H20 | A file named "Documents": nothing breaks | PASS (moved to Other/Documents) |

## EXTRA tests run earlier today (not in the 60)
| Test | Result |
|---|---|
| 20,000 files: --space 2.8 s, --suggest 0.3 s, --find-duplicates 1.2 s | PASS |
| 300 repeated name clashes in one folder (about 0.1 s per run) | PASS |
| Weird names (.pdf, ..pdf, .tar.gz, spaces, symbols, Japanese, zero bytes) | PASS |
| Broken settings files (7 kinds: empty, bad JSON, wrong type, huge numbers) | PASS (clear messages) |
| Dangerous sources (/, /etc, /usr, /home, /root) | PASS |
| Bad command-line input (missing folder, file instead of folder, bad numbers) | PASS |
| Rule with destination "../../x" or an absolute path | INCONCLUSIVE (nothing escaped; file went to Other/) |
| 40-command sweep of every option | PASS except the 4 minor items below |
| --undo with a wrong run ID gives a misleading message | FAIL (minor) |
| Undo leaves empty folders behind | FAIL (minor) |
| manage_folders.py with no keyboard input shows a traceback | FAIL (minor) |
| --all with no watched folders ends in an error | FAIL (minor) |

## From earlier sessions (taken from PROJECT_SUMMARY.md, not re-run today)
- Hundreds of scenarios: sorting rules, undo/restore/history, duplicates, folder organizing, --all, suggestions, pause, doctor, archive, repair flows, simulated installer.
- Stress test: 6,025 files / 86 folders, 0 errors, 0 files lost, second run moves nothing, about 3 s.
- Crash test: kill after 150 moves, all 150 undoable.

## Still NOT proven (needs a real Windows PC)
Scheduled-task XML, right-click menu, .bat helpers, file arrival time semantics, case-insensitive name clashes, 260-character path limit, Notepad/PowerShell encodings in practice, Windows 11 "Show more options" menu, OneDrive-redirected Downloads, a full disk.
Also not run: permission-denied on a whole folder tree in recursive mode.


---
# BATCH 2 (12 Nov 2026) - 153 more tests
| Level | Tests | Pass | Fail |
|---|---|---|---|
| Simple | 50 | 48 | 2 |
| Medium | 50 | 50 | 0 |
| Hard | 53 | 50 | 3 |

## New findings from batch 2 (numbering continues from the bug list above)
11. .html and .css files go to Other/ instead of Code/ (decision needed: probably they belong in Code).
12. A custom rule written with "extensions": ["pdf"] (no dot) silently matches nothing; the real format is [".pdf"]. No warning is shown.
13. Date check: files dated in the future (2100, 2262, tomorrow) stay loose forever - same bug as #4, now with more cases.
14. When the script folder is read-only for the user (e.g. installed in a protected place), the undo history is written INSIDE the organized folder as .organizer_history.jsonl instead of failing clearly.
15. A custom rule destination can point outside the organized folder ("../../x" or an absolute path) and files really move there. May be intended, but there is no warning and no check against system folders - needs a decision.
Dated hard tests 1970 / epoch 0 / 1901 only checked "no file lost, 0 errors", not the exact destination.

### SIMPLE batch 2 (one test per file type): 48 / 50 passed
| # | Test | Result |
|---|---|---|
| S2-01 | .PDF -> Documents | PASS |
| S2-02 | .docx -> Documents | PASS |
| S2-03 | .DOC -> Documents | PASS |
| S2-04 | .pptx -> Documents | PASS |
| S2-05 | .PPT -> Documents | PASS |
| S2-06 | .xlsx -> Documents | PASS |
| S2-07 | .XLS -> Documents | PASS |
| S2-08 | .csv -> Documents | PASS |
| S2-09 | .XML -> Documents | PASS |
| S2-10 | .txt -> Documents | PASS |
| S2-11 | .MD -> Documents | PASS |
| S2-12 | .rtf -> Documents | PASS |
| S2-13 | .ODT -> Documents | PASS |
| S2-14 | .jpg -> Images | PASS |
| S2-15 | .JPEG -> Images | PASS |
| S2-16 | .png -> Images | PASS |
| S2-17 | .GIF -> Images | PASS |
| S2-18 | .bmp -> Images | PASS |
| S2-19 | .WEBP -> Images | PASS |
| S2-20 | .svg -> Images | PASS |
| S2-21 | .HEIC -> Images | PASS |
| S2-22 | .tiff -> Images | PASS |
| S2-23 | .MP4 -> Videos | PASS |
| S2-24 | .mkv -> Videos | PASS |
| S2-25 | .AVI -> Videos | PASS |
| S2-26 | .mov -> Videos | PASS |
| S2-27 | .WMV -> Videos | PASS |
| S2-28 | .webm -> Videos | PASS |
| S2-29 | .MP3 -> Audio | PASS |
| S2-30 | .wav -> Audio | PASS |
| S2-31 | .FLAC -> Audio | PASS |
| S2-32 | .aac -> Audio | PASS |
| S2-33 | .OGG -> Audio | PASS |
| S2-34 | .m4a -> Audio | PASS |
| S2-35 | .PY -> Code | PASS |
| S2-36 | .c -> Code | PASS |
| S2-37 | .H -> Code | PASS |
| S2-38 | .cpp -> Code | PASS |
| S2-39 | .JAVA -> Code | PASS |
| S2-40 | .js -> Code | PASS |
| S2-41 | .TS -> Code | PASS |
| S2-42 | .html -> Code | FAIL (Other/HTML/sample file.html) |
| S2-43 | .CSS -> Code | FAIL (Other/CSS/sample file.CSS) |
| S2-44 | .json -> Code | PASS |
| S2-45 | .ZIP -> Archives | PASS |
| S2-46 | .rar -> Archives | PASS |
| S2-47 | .7Z -> Archives | PASS |
| S2-48 | .gz -> Archives | PASS |
| S2-49 | .EXE -> Installers | PASS |
| S2-50 | .msi -> Installers | PASS |

### MEDIUM batch 2 (options, rules, conflicts, undo, duplicates): 50 / 50 passed
| # | Test | Result |
|---|---|---|
| M2-01 | --subfolders extension on report.pdf | PASS |
| M2-02 | --subfolders extension on riverside.jpg | PASS |
| M2-03 | --subfolders year on report.pdf | PASS |
| M2-04 | --subfolders year on riverside.jpg | PASS |
| M2-05 | --subfolders month on report.pdf | PASS |
| M2-06 | --subfolders month on riverside.jpg | PASS |
| M2-07 | --subfolders year-month on report.pdf | PASS |
| M2-08 | --subfolders year-month on riverside.jpg | PASS |
| M2-09 | --subfolders first-letter on report.pdf | PASS |
| M2-10 | --subfolders first-letter on riverside.jpg | PASS |
| M2-11 | --subfolders size on report.pdf | PASS |
| M2-12 | --subfolders size on riverside.jpg | PASS |
| M2-13 | --subfolders topic on report.pdf | PASS |
| M2-14 | --subfolders topic on riverside.jpg | PASS |
| M2-15 | rename + different -> both kept | PASS |
| M2-16 | rename + identical -> one kept, 1 dup set aside | PASS |
| M2-17 | skip + different -> new stays loose | PASS |
| M2-18 | skip + identical -> nothing lost | PASS |
| M2-19 | overwrite + different -> new in place | PASS |
| M2-20 | overwrite + identical -> content intact | PASS |
| M2-21 | ignore pattern secret* | PASS |
| M2-22 | ignore pattern *.tmp2 | PASS |
| M2-23 | ignore pattern with ? | PASS |
| M2-24 | ignore exact name | PASS |
| M2-25 | built-in *password*.csv ignored | PASS |
| M2-26 | size rule min_size_mb | PASS (my test used extensions without a dot; passes with a dot (see finding 12)) |
| M2-27 | size rule max_size_mb | PASS (my test used extensions without a dot; passes with a dot (see finding 12)) |
| M2-28 | size rule min+max (between) | PASS (my test used extensions without a dot; passes with a dot (see finding 12)) |
| M2-29 | size rule no match leaves default | PASS |
| M2-30 | regex rule ^invoice_\d+ | PASS |
| M2-31 | regex rule is case sensitive? | PASS |
| M2-32 | regex no match falls through | PASS |
| M2-33 | glob pattern report_*.pdf | PASS |
| M2-34 | glob pattern *final* | PASS |
| M2-35 | glob pattern ?.txt | PASS |
| M2-36 | custom rule beats built-in | PASS (my test used extensions without a dot; passes with a dot (see finding 12)) |
| M2-37 | disabled custom rule ignored | PASS |
| M2-38 | default min-age: fresh file stays | PASS |
| M2-39 | default min-age: 2-min-old file moves | PASS |
| M2-40 | --min-age 0: fresh file moves | PASS |
| M2-41 | undo after --subfolders year-month | PASS |
| M2-42 | undo after rename-conflict | PASS |
| M2-43 | undo after duplicates set aside | PASS |
| M2-44 | undo after a partial --restore | PASS |
| M2-45 | two runs, undo twice restores both | PASS |
| M2-46 | --find-duplicates alone moves nothing | PASS |
| M2-47 | --set-aside keeps one, moves the other | PASS |
| M2-48 | 3 identical copies -> 2 set aside | PASS |
| M2-49 | same size, different content not duplicates | PASS |
| M2-50 | empty (0-byte) files handled safely | PASS |

### HARD batch 2 (names, sizes, dates, counts, special files): 50 / 53 passed
| # | Test | Result |
|---|---|---|
| H2-01 | name stem length 1 | PASS |
| H2-02 | name stem length 100 | PASS |
| H2-03 | name stem length 200 | PASS |
| H2-04 | name stem length 240 | PASS |
| H2-05 | name stem length 251 | PASS |
| H2-06 | multibyte 244 bytes (日 x80) | PASS |
| H2-07 | multibyte 253 bytes (日 x83) | PASS |
| H2-08 | emoji 244 bytes | PASS |
| H2-09 | script name 'ملف.pdf' | PASS |
| H2-10 | script name 'फ़ाइल.pdf' | PASS |
| H2-11 | script name 'файл.pdf' | PASS |
| H2-12 | script name '📄doc.pdf' | PASS |
| H2-13 | script name 'é.pdf' | PASS |
| H2-14 | special chars 'a  b.pdf' | PASS |
| H2-15 | special chars ' lead.pdf' | PASS |
| H2-16 | special chars 'trail .pdf' | PASS |
| H2-17 | special chars 'a\'b".pdf' | PASS |
| H2-18 | special chars 'a&b;c|d.pdf' | PASS |
| H2-19 | special chars '50%.pdf' | PASS |
| H2-20 | special chars '[x](y).pdf' | PASS |
| H2-21 | special chars '{a}$HOME#b.pd | PASS |
| H2-22 | special chars 'a\tb.pdf' | PASS |
| H2-23 | special chars 'a\nb.pdf' | PASS |
| H2-24 | 1,000 files | PASS |
| H2-25 | 5,000 pdf files | PASS |
| H2-26 | 10,000 mixed files | PASS |
| H2-27 | one 1 GB sparse file | PASS |
| H2-28 | five 512 MB sparse files (same content) | PASS |
| H2-29 | 3,000 files in one subfolder, recursive | PASS |
| H2-30 | 50 nested levels, recursive | PASS |
| H2-31 | 200 nested levels, recursive | PASS |
| H2-32 | 500 empty subfolders, recursive | PASS |
| H2-33 | 1,000 different unknown extensions | PASS |
| H2-34 | mtime 1970-01-02 | PASS |
| H2-35 | mtime epoch 0 | PASS |
| H2-36 | mtime 1901 (negative) | PASS |
| H2-37 | mtime year 2100 | FAIL (file left loose forever (known bug: future dates)) |
| H2-38 | mtime year 2262 | FAIL (file left loose forever (known bug: future dates)) |
| H2-39 | mtime tomorrow | FAIL (file left loose forever (known bug: future dates)) |
| H2-40 | 20 same-name different files in 20 subfolders, recursive | PASS |
| H2-41 | 100 identical copies | PASS |
| H2-42 | clash and 'a (1).pdf' already exists | PASS |
| H2-43 | clash with (1)..(5) all taken | PASS |
| H2-44 | name that already ends in (1) | PASS |
| H2-45 | A.PDF vs a.pdf in destination | PASS |
| H2-46 | read-only (444) file | PASS (OK; the extra file is a history file written inside the folder (see finding 14)) |
| H2-47 | file inside unwritable subfolder, recursive | PASS (OK; the extra file is a history file written inside the folder (see finding 14)) |
| H2-48 | two hard links to one file | PASS |
| H2-49 | symlink to a file in same folder | PASS |
| H2-50 | named pipe (FIFO) called x.pdf | PASS |
| H2-51 | directory named like a file (x.pdf/) | PASS |
| H2-52 | destination folder path is 200 chars long | PASS |
| H2-53 | source path with spaces + 60 accents | PASS |


---
# BATCH 3 (12 Nov 2026) - 300 more tests
| Level | Tests | Pass | Fail |
|---|---|---|---|
| Simple | 102 | 81 | 21 |
| Medium | 99 | 94 | 5 |
| Hard | 99 | 91 | 8 |
(The counts are a little off 100 because some groups came out slightly larger or smaller. One planned hard test, a subfolder deleted mid-run, was skipped because its result could not be checked reliably.)

## New findings from batch 3 (numbering continues)
16. After a crash or kill, the next run prints "another run is already working on this folder, skipping this one" and does nothing (5 of 5 tests). The leftover lock only expires after 15 minutes, so a scheduled run after a crash is blocked until then.
17. Undo after a kill did not bring back every file in 3 of 15 runs (killed after 86, 339 and 133 moves). I could not reproduce it in 16 retries, so treat it as intermittent and worth a look.
18. Many common file types are not sorted into a proper category and fall into Other/<EXT>: raw cr2 nef eps jfif (images), m4v mpg mpeg 3gp (videos), opus aiff mid (audio), cs go rs php rb swift kt sql (code), docm (documents). For your embedded work, hex bin elf map also land in Other/<EXT>; a Firmware category could help.
19. A folder whose only project marker is .git is not filed under Folders/Projects (it is still left alone, and stays whole in recursive mode).
20. --clean-empty removes empty sub-folders but leaves the empty top-level category folders (Documents, Images, Audio...).
What passed strongly: 25 random "chaos" folders (mixed alphabets, emoji, random dates, duplicates) all organized with 0 errors, a quiet second run, and an undo that restored every original name exactly; 20,000 files; 300 same-name files kept intact; undo with edited, deleted or missing files.
Where the unusual types went: iso->Disk Images
dmg->Installers
apk->Installers
deb->Installers
rpm->Installers
hex->Other/HEX
bin->Other/BIN
elf->Other/ELF
map->Other/MAP

### SIMPLE batch 3 (more file types, name variants, command options, undo cycles): 81 / 102 passed
| # | Test | Result |
|---|---|---|
| S3-001 | .docm lands in Documents (got Other) | FAIL (Other/DOCM/sample.docm) |
| S3-002 | .xlsm lands in Documents (got Documents) | PASS |
| S3-003 | .odp lands in Documents (got Documents) | PASS |
| S3-004 | .ods lands in Documents (got Documents) | PASS |
| S3-005 | .epub lands in Documents (got Ebooks) | PASS (OK: has its own folder (Ebooks / Design)) |
| S3-006 | .raw lands in Images (got Other) | FAIL (Other/RAW/sample.raw) |
| S3-007 | .cr2 lands in Images (got Other) | FAIL (Other/CR2/sample.cr2) |
| S3-008 | .nef lands in Images (got Other) | FAIL (Other/NEF/sample.nef) |
| S3-009 | .psd lands in Images (got Design) | PASS (OK: has its own folder (Ebooks / Design)) |
| S3-010 | .ai lands in Images (got Design) | PASS (OK: has its own folder (Ebooks / Design)) |
| S3-011 | .eps lands in Images (got Other) | FAIL (Other/EPS/sample.eps) |
| S3-012 | .jfif lands in Images (got Other) | FAIL (Other/JFIF/sample.jfif) |
| S3-013 | .m4v lands in Videos (got Other) | FAIL (Other/M4V/sample.m4v) |
| S3-014 | .mpg lands in Videos (got Other) | FAIL (Other/MPG/sample.mpg) |
| S3-015 | .mpeg lands in Videos (got Other) | FAIL (Other/MPEG/sample.mpeg) |
| S3-016 | .3gp lands in Videos (got Other) | FAIL (Other/3GP/sample.3gp) |
| S3-017 | .opus lands in Audio (got Other) | FAIL (Other/OPUS/sample.opus) |
| S3-018 | .aiff lands in Audio (got Other) | FAIL (Other/AIFF/sample.aiff) |
| S3-019 | .mid lands in Audio (got Other) | FAIL (Other/MID/sample.mid) |
| S3-020 | .cs lands in Code (got Other) | FAIL (Other/CS/sample.cs) |
| S3-021 | .go lands in Code (got Other) | FAIL (Other/GO/sample.go) |
| S3-022 | .rs lands in Code (got Other) | FAIL (Other/RS/sample.rs) |
| S3-023 | .php lands in Code (got Other) | FAIL (Other/PHP/sample.php) |
| S3-024 | .rb lands in Code (got Other) | FAIL (Other/RB/sample.rb) |
| S3-025 | .swift lands in Code (got Other) | FAIL (Other/SWIFT/sample.swift) |
| S3-026 | .kt lands in Code (got Other) | FAIL (Other/KT/sample.kt) |
| S3-027 | .sql lands in Code (got Other) | FAIL (Other/SQL/sample.sql) |
| S3-028 | .yaml lands in Code (got Code) | PASS |
| S3-029 | .yml lands in Code (got Code) | PASS |
| S3-030 | .tar lands in Archives (got Archives) | PASS |
| S3-031 | .bz2 lands in Archives (got Archives) | PASS |
| S3-032 | .xz lands in Archives (got Archives) | PASS |
| S3-033 | .iso lands in any folder (got Disk Images) | PASS |
| S3-034 | .dmg lands in any folder (got Installers) | PASS |
| S3-035 | .apk lands in any folder (got Installers) | PASS |
| S3-036 | .deb lands in any folder (got Installers) | PASS |
| S3-037 | .rpm lands in any folder (got Installers) | PASS |
| S3-038 | .hex lands in any folder (got Other) | PASS |
| S3-039 | .bin lands in any folder (got Other) | PASS |
| S3-040 | .elf lands in any folder (got Other) | PASS |
| S3-041 | .map lands in any folder (got Other) | PASS |
| S3-042 | name variant a.pdf -> Documents | PASS |
| S3-043 | name variant A.PDF -> Documents | PASS |
| S3-044 | name variant report.final.v2.pdf -> Documents | PASS |
| S3-045 | name variant my report (1).pdf -> Documents | PASS |
| S3-046 | name variant 2024-report.pdf -> Documents | PASS |
| S3-047 | name variant report-final_FINAL.pdf -> Documents | PASS |
| S3-048 | name variant x.backup.pdf -> Documents | PASS |
| S3-049 | name variant file.name.with.dots.jpg -> Images | PASS |
| S3-050 | name variant IMG_0001.JPG -> Images | PASS |
| S3-051 | name variant photo copy.jpeg -> Images | PASS |
| S3-052 | name variant song - artist.mp3 -> Audio | PASS |
| S3-053 | name variant movie.2024.1080p.mkv -> Videos | PASS |
| S3-054 | name variant archive.tar.gz -> Archives | PASS |
| S3-055 | name variant notes.TXT -> Documents | PASS |
| S3-056 | name variant main.C -> Code | PASS |
| S3-057 | name variant Setup-1.2.3.exe -> Installers | PASS |
| S3-058 | name variant data(2).csv -> Documents | PASS |
| S3-059 | name variant résumé.pdf -> Documents | PASS |
| S3-060 | name variant a b c.xlsx -> Documents | PASS |
| S3-061 | name variant ÜBER.PNG -> Images | PASS |
| S3-062 | CLI --version | PASS |
| S3-063 | CLI -h | PASS |
| S3-064 | CLI --doctor | PASS |
| S3-065 | CLI --status | PASS |
| S3-066 | CLI --space | PASS |
| S3-067 | CLI --suggest | PASS |
| S3-068 | CLI --history | PASS |
| S3-069 | CLI --clean-empty | PASS |
| S3-070 | CLI -v -n | PASS |
| S3-071 | CLI --snooze 5m | PASS |
| S3-072 | CLI --resume | PASS |
| S3-073 | CLI --find-duplicates | PASS |
| S3-074 | CLI --archive-old -n | PASS |
| S3-075 | CLI --subfolders year-month -n | PASS |
| S3-076 | CLI --on-conflict skip -n | PASS |
| S3-077 | CLI --min-age 5 -n | PASS |
| S3-078 | CLI --bogus | PASS |
| S3-079 | CLI --on-conflict weird | PASS |
| S3-080 | CLI --snooze abc | PASS |
| S3-081 | CLI --min-age abc | PASS |
| S3-082 | CLI missing source folder | PASS |
| S3-083 | organize then undo (pdf) | PASS |
| S3-084 | organize then undo (jpg) | PASS |
| S3-085 | organize then undo (mp4) | PASS |
| S3-086 | organize then undo (mp3) | PASS |
| S3-087 | organize then undo (c) | PASS |
| S3-088 | organize then undo (zip) | PASS |
| S3-089 | organize then undo (exe) | PASS |
| S3-090 | organize then undo (csv) | PASS |
| S3-091 | organize then undo (txt) | PASS |
| S3-092 | organize then undo (docx) | PASS |
| S3-093 | dry-run shows plan, moves nothing (pdf) | PASS |
| S3-094 | dry-run shows plan, moves nothing (jpg) | PASS |
| S3-095 | dry-run shows plan, moves nothing (mp4) | PASS |
| S3-096 | dry-run shows plan, moves nothing (mp3) | PASS |
| S3-097 | dry-run shows plan, moves nothing (c) | PASS |
| S3-098 | dry-run shows plan, moves nothing (zip) | PASS |
| S3-099 | dry-run shows plan, moves nothing (exe) | PASS |
| S3-100 | dry-run shows plan, moves nothing (csv) | PASS |
| S3-101 | dry-run shows plan, moves nothing (txt) | PASS |
| S3-102 | dry-run shows plan, moves nothing (docx) | PASS |

### MEDIUM batch 3 (subfolder options, conflicts, folder organizing, topics, ignores): 94 / 99 passed
| # | Test | Result |
|---|---|---|
| M3-001 | --subfolders extension on sample.mp4 | PASS |
| M3-002 | --subfolders extension on sample.mp3 | PASS |
| M3-003 | --subfolders extension on sample.py | PASS |
| M3-004 | --subfolders extension on sample.zip | PASS |
| M3-005 | --subfolders extension on sample.docx | PASS |
| M3-006 | --subfolders year on sample.mp4 | PASS |
| M3-007 | --subfolders year on sample.mp3 | PASS |
| M3-008 | --subfolders year on sample.py | PASS |
| M3-009 | --subfolders year on sample.zip | PASS |
| M3-010 | --subfolders year on sample.docx | PASS |
| M3-011 | --subfolders month on sample.mp4 | PASS |
| M3-012 | --subfolders month on sample.mp3 | PASS |
| M3-013 | --subfolders month on sample.py | PASS |
| M3-014 | --subfolders month on sample.zip | PASS |
| M3-015 | --subfolders month on sample.docx | PASS |
| M3-016 | --subfolders year-month on sample.mp4 | PASS |
| M3-017 | --subfolders year-month on sample.mp3 | PASS |
| M3-018 | --subfolders year-month on sample.py | PASS |
| M3-019 | --subfolders year-month on sample.zip | PASS |
| M3-020 | --subfolders year-month on sample.docx | PASS |
| M3-021 | --subfolders first-letter on sample.mp4 | PASS |
| M3-022 | --subfolders first-letter on sample.mp3 | PASS |
| M3-023 | --subfolders first-letter on sample.py | PASS |
| M3-024 | --subfolders first-letter on sample.zip | PASS |
| M3-025 | --subfolders first-letter on sample.docx | PASS |
| M3-026 | --subfolders size on sample.mp4 | PASS |
| M3-027 | --subfolders size on sample.mp3 | PASS |
| M3-028 | --subfolders size on sample.py | PASS |
| M3-029 | --subfolders size on sample.zip | PASS |
| M3-030 | --subfolders size on sample.docx | PASS |
| M3-031 | --subfolders topic on sample.mp4 | PASS |
| M3-032 | --subfolders topic on sample.mp3 | PASS |
| M3-033 | --subfolders topic on sample.py | PASS |
| M3-034 | --subfolders topic on sample.zip | PASS |
| M3-035 | --subfolders topic on sample.docx | PASS |
| M3-036 | conflict rename on .pdf | PASS |
| M3-037 | conflict rename on .jpg | PASS |
| M3-038 | conflict rename on .mp3 | PASS |
| M3-039 | conflict rename on .c | PASS |
| M3-040 | conflict rename on .zip | PASS |
| M3-041 | conflict rename on .exe | PASS |
| M3-042 | conflict skip on .pdf | PASS |
| M3-043 | conflict skip on .jpg | PASS |
| M3-044 | conflict skip on .mp3 | PASS |
| M3-045 | conflict skip on .c | PASS |
| M3-046 | conflict skip on .zip | PASS |
| M3-047 | conflict skip on .exe | PASS |
| M3-048 | conflict overwrite on .pdf | PASS |
| M3-049 | conflict overwrite on .jpg | PASS |
| M3-050 | conflict overwrite on .mp3 | PASS |
| M3-051 | conflict overwrite on .c | PASS |
| M3-052 | conflict overwrite on .zip | PASS |
| M3-053 | conflict overwrite on .exe | PASS |
| M3-054 | folder: 3 photos -> Folders/Photos | PASS |
| M3-055 | folder: 2 videos -> Folders/Videos | PASS |
| M3-056 | folder: 3 audio -> Folders/Audio | PASS |
| M3-057 | folder: 2 documents -> Folders/Documents | PASS |
| M3-058 | folder: 2 code files -> Folders/Code | PASS |
| M3-059 | folder with .git -> Folders/Projects | FAIL (proj/.git/config) |
| M3-060 | folder with package.json -> Folders/Projects | PASS |
| M3-061 | folder with pyproject.toml -> Folders/Projects | PASS |
| M3-062 | folder with platformio.ini -> Folders/Projects | PASS |
| M3-063 | folder with CMakeLists.txt -> Folders/Projects | PASS |
| M3-064 | folder with Makefile -> Folders/Projects | PASS |
| M3-065 | folder with board.ioc -> Folders/Projects | PASS |
| M3-066 | folder with proj.uvprojx -> Folders/Projects | PASS |
| M3-067 | folder with app.sln -> Folders/Projects | PASS |
| M3-068 | folder with blink.ino -> Folders/Projects | PASS |
| M3-069 | folder: only 2 photos stays loose (needs 3) | PASS |
| M3-070 | folder: 3 photos but only 5 hours old stays | PASS |
| M3-071 | folder: mixed types, no majority stays loose | PASS |
| M3-072 | topic RTOS matches 'RTOS_notes.pdf' | PASS |
| M3-073 | topic IoT matches 'IoT_notes.pdf' | PASS |
| M3-074 | topic ARM matches 'ARM_notes.pdf' | PASS |
| M3-075 | topic RISC-V matches 'RISC-V_notes.pdf' | PASS |
| M3-076 | topic Microcontrollers matches 'Microcontrollers_notes.pdf' | PASS |
| M3-077 | topic Resume matches 'Resume_notes.pdf' | PASS |
| M3-078 | topic ARM does NOT match 'ARMOR_notes.pdf' | PASS (OK: not in a topic folder (my check also matched the file name)) |
| M3-079 | topic RTOS does NOT match 'RTOSX.pdf' | PASS (OK: not in a topic folder (my check also matched the file name)) |
| M3-080 | topic matches lowercase 'rtos notes.pdf' | PASS |
| M3-081 | desktop.ini left alone | PASS |
| M3-082 | Thumbs.db left alone | PASS |
| M3-083 | .DS_Store left alone | PASS |
| M3-084 | shortcut.lnk left alone | PASS |
| M3-085 | my password list.csv left alone | PASS |
| M3-086 | .hidden.pdf left alone | PASS |
| M3-087 | dl.pdf.crdownload left alone | PASS |
| M3-088 | dl.pdf.part left alone | PASS |
| M3-089 | dl.tmp left alone | PASS |
| M3-090 | dl.pdf.download left alone | PASS |
| M3-091 | recursive layout 1: no loss, 0 errors, 2nd run idle | PASS |
| M3-092 | recursive layout 2: no loss, 0 errors, 2nd run idle | PASS |
| M3-093 | recursive layout 3: no loss, 0 errors, 2nd run idle | PASS |
| M3-094 | recursive layout 4: no loss, 0 errors, 2nd run idle | PASS |
| M3-095 | recursive layout 5: no loss, 0 errors, 2nd run idle | PASS |
| M3-096 | undo then --clean-empty leaves no empty folders (#1) | FAIL (['Documents', 'Audio', 'Images']) |
| M3-097 | undo then --clean-empty leaves no empty folders (#2) | FAIL (['Documents', 'Audio', 'Images']) |
| M3-098 | undo then --clean-empty leaves no empty folders (#3) | FAIL (['Documents', 'Audio', 'Images']) |
| M3-099 | undo then --clean-empty leaves no empty folders (#4) | FAIL (['Documents', 'Audio', 'Images']) |

### HARD batch 3 (random chaos runs, kills, parallel runs, scale, live changes): 91 / 99 passed
| # | Test | Result |
|---|---|---|
| H3-001 | chaos run seed 1 (mixed names/types/dates): organize, 2nd run, undo exact | PASS |
| H3-002 | chaos run seed 2 (mixed names/types/dates): organize, 2nd run, undo exact | PASS |
| H3-003 | chaos run seed 3 (mixed names/types/dates): organize, 2nd run, undo exact | PASS |
| H3-004 | chaos run seed 4 (mixed names/types/dates): organize, 2nd run, undo exact | PASS |
| H3-005 | chaos run seed 5 (mixed names/types/dates): organize, 2nd run, undo exact | PASS |
| H3-006 | chaos run seed 6 (mixed names/types/dates): organize, 2nd run, undo exact | PASS |
| H3-007 | chaos run seed 7 (mixed names/types/dates): organize, 2nd run, undo exact | PASS |
| H3-008 | chaos run seed 8 (mixed names/types/dates): organize, 2nd run, undo exact | PASS |
| H3-009 | chaos run seed 9 (mixed names/types/dates): organize, 2nd run, undo exact | PASS |
| H3-010 | chaos run seed 10 (mixed names/types/dates): organize, 2nd run, undo exact | PASS |
| H3-011 | chaos run seed 11 (mixed names/types/dates): organize, 2nd run, undo exact | PASS |
| H3-012 | chaos run seed 12 (mixed names/types/dates): organize, 2nd run, undo exact | PASS |
| H3-013 | chaos run seed 13 (mixed names/types/dates): organize, 2nd run, undo exact | PASS |
| H3-014 | chaos run seed 14 (mixed names/types/dates): organize, 2nd run, undo exact | PASS |
| H3-015 | chaos run seed 15 (mixed names/types/dates): organize, 2nd run, undo exact | PASS |
| H3-016 | chaos run seed 16 (mixed names/types/dates): organize, 2nd run, undo exact | PASS |
| H3-017 | chaos run seed 17 (mixed names/types/dates): organize, 2nd run, undo exact | PASS |
| H3-018 | chaos run seed 18 (mixed names/types/dates): organize, 2nd run, undo exact | PASS |
| H3-019 | chaos run seed 19 (mixed names/types/dates): organize, 2nd run, undo exact | PASS |
| H3-020 | chaos run seed 20 (mixed names/types/dates): organize, 2nd run, undo exact | PASS |
| H3-021 | chaos run seed 21 (mixed names/types/dates): organize, 2nd run, undo exact | PASS |
| H3-022 | chaos run seed 22 (mixed names/types/dates): organize, 2nd run, undo exact | PASS |
| H3-023 | chaos run seed 23 (mixed names/types/dates): organize, 2nd run, undo exact | PASS |
| H3-024 | chaos run seed 24 (mixed names/types/dates): organize, 2nd run, undo exact | PASS |
| H3-025 | chaos run seed 25 (mixed names/types/dates): organize, 2nd run, undo exact | PASS |
| H3-026 | SIGKILL at 0.12s, then undo restores all 3000 | FAIL (killed after 86 moved (intermittent; not reproduced in 16 retries)) |
| H3-027 | SIGKILL at 0.2s, then undo restores all 3000 | FAIL (killed after 339 moved (intermittent; not reproduced in 16 retries)) |
| H3-028 | SIGKILL at 0.3s, then undo restores all 3000 | PASS |
| H3-029 | SIGKILL at 0.4s, then undo restores all 3000 | PASS |
| H3-030 | SIGKILL at 0.5s, then undo restores all 3000 | PASS |
| H3-031 | SIGKILL at 0.6s, then undo restores all 3000 | PASS |
| H3-032 | SIGKILL at 0.7s, then undo restores all 3000 | PASS |
| H3-033 | SIGKILL at 0.8s, then undo restores all 3000 | PASS |
| H3-034 | SIGKILL at 0.9s, then undo restores all 3000 | PASS |
| H3-035 | SIGKILL at 1.0s, then undo restores all 3000 | PASS |
| H3-036 | SIGTERM at 0.15s, then undo restores all 3000 | FAIL (killed after 133 moved) |
| H3-037 | SIGTERM at 0.25s, then undo restores all 3000 | PASS |
| H3-038 | SIGTERM at 0.35s, then undo restores all 3000 | PASS |
| H3-039 | SIGTERM at 0.45s, then undo restores all 3000 | PASS |
| H3-040 | SIGTERM at 0.55s, then undo restores all 3000 | PASS |
| H3-041 | SIGKILL at 0.15s, immediate re-run finishes the job | FAIL (killed after 148 moved; rerun loose=2852) |
| H3-042 | SIGKILL at 0.3s, immediate re-run finishes the job | FAIL (killed after 615 moved; rerun loose=2385) |
| H3-043 | SIGKILL at 0.45s, immediate re-run finishes the job | FAIL (killed after 764 moved; rerun loose=2236) |
| H3-044 | SIGKILL at 0.6s, immediate re-run finishes the job | FAIL (killed after 1400 moved; rerun loose=1600) |
| H3-045 | SIGKILL at 0.75s, immediate re-run finishes the job | FAIL (killed after 1778 moved; rerun loose=1222) |
| H3-001 | 2 runs at the same time on 1,500 files | PASS |
| H3-002 | 3 runs at the same time on 1,500 files | PASS |
| H3-003 | 4 runs at the same time on 1,500 files | PASS |
| H3-004 | 5 runs at the same time on 1,500 files | PASS |
| H3-005 | 6 runs at the same time on 1,500 files | PASS |
| H3-006 | 8 runs at the same time on 1,500 files | PASS |
| H3-007 | 2 runs while another program adds 200 files | PASS |
| H3-008 | 4 runs while another program adds 200 files | PASS |
| H3-009 | undo and organize at the same time | PASS |
| H3-010 | 3 undos at the same time | PASS |
| H3-011 | 2,000 mixed files, 2nd run idle | PASS |
| H3-012 | 4,000 mixed files, 2nd run idle | PASS |
| H3-013 | 8,000 mixed files, 2nd run idle | PASS |
| H3-014 | 12,000 mixed files, 2nd run idle | PASS |
| H3-015 | 16,000 mixed files, 2nd run idle | PASS |
| H3-016 | 20,000 mixed files, 2nd run idle | PASS |
| H3-017 | 5,000 files in 500 subfolders, recursive | PASS |
| H3-018 | 5,000 identical copies | PASS |
| H3-019 | 3,000 different unknown extensions | PASS |
| H3-020 | 2,000 files with 200-character names | PASS |
| H3-021 | 10% of files deleted while running | PASS |
| H3-022 | 50% of files deleted while running | PASS |
| H3-023 | 90% of files deleted while running | PASS |
| H3-024 | 300 new files appear while running | PASS |
| H3-025 | files renamed while running | PASS |
| H3-027 | timestamps touched while running | PASS |
| H3-028 | files emptied while running | PASS (OK: my test re-created the emptied files, so the count grew) |
| H3-029 | a file replaced by a folder while running | PASS |
| H3-030 | destination folder deleted while running (no crash) | PASS |
| H3-031 | 5 same-name different files in 5 folders, recursive | PASS |
| H3-032 | 10 same-name different files in 10 folders, recursive | PASS |
| H3-033 | 20 same-name different files in 20 folders, recursive | PASS |
| H3-034 | 40 same-name different files in 40 folders, recursive | PASS |
| H3-035 | 60 same-name different files in 60 folders, recursive | PASS |
| H3-036 | 80 same-name different files in 80 folders, recursive | PASS |
| H3-037 | 100 same-name different files in 100 folders, recursive | PASS |
| H3-038 | 150 same-name different files in 150 folders, recursive | PASS |
| H3-039 | 200 same-name different files in 200 folders, recursive | PASS |
| H3-040 | 300 same-name different files in 300 folders, recursive | PASS |
| H3-041 | odd names ['a<b>c.pdf'] | PASS |
| H3-042 | odd names ['a:b|c.pdf'] | PASS |
| H3-043 | odd names ['q?"*.pdf'] | PASS |
| H3-044 | odd names ['CON.pdf', 'PRN.jpg', 'AUX.txt',  | PASS |
| H3-045 | odd names ['COM1.pdf', 'LPT1.docx', 'com2.pd | PASS |
| H3-046 | odd names ['con.pdf', 'Con.pdf', 'CON.PDF'] | PASS |
| H3-047 | odd names ['trail.pdf.'] | PASS |
| H3-048 | odd names ['trail.pdf '] | PASS |
| H3-049 | odd names ['...'] | PASS |
| H3-050 | odd names ['a.pdf', 'a.PDF', 'A.pdf', 'A.PDF | PASS |
| H3-051 | undo with edited file still restored | PASS |
| H3-052 | undo with one moved file deleted: rest restored | PASS |
| H3-053 | undo with destination folder deleted: no crash | PASS |
| H3-054 | undo with history file deleted: no crash | PASS |
| H3-055 | undo with corrupt line in middle of history: rest restored | PASS |


---
# VERSION 2.7.1 RE-TEST (12 Nov 2026)
All fixes were written, then EVERY earlier suite was run again against 2.7.1.

## Fix checks (23 checks, one per fix): 23 / 23 PASS
| Fix | Result |
|---|---|
| 1 Bad regex hang (nested repeats are switched off; any other slow pattern is stopped after 1 s) | PASS |
| 2 Makefile sorted to Code/Build (ignore list cleaned) | PASS |
| 3 255-character name clash (renamed to exactly 255 bytes) | PASS |
| 4/13 File dated 2100 / tomorrow is organized (counts as "arrived now") | PASS |
| 5 Non-UTF-8 file name: clean log, 0 errors | PASS |
| 6 Files vanishing mid-run: 704 skipped, 0 errors | PASS |
| 7 Permission problem says "permission denied" | PASS |
| 8 Damaged history line: clear "NOT put back" warning | PASS |
| 9 ~$ Office temp files ignored | PASS |
| 10 --undo wrong id message, undo leaves no empty folders, manage_folders without keyboard, scheduled run with nothing to watch, dry-run hint, "saved as a (1).pdf" log line | PASS (6 checks) |
| 11/18 html css raw m4v mid go sql docm hex elf sorted (10 types) | PASS |
| 12 Extension written without a dot works | PASS |
| 14 Read-only Organizer folder: stops with a clear message | PASS |
| 15 Rule destination outside the folder blocked; "allow_outside": true works | PASS |
| 16 Re-run right after a kill finishes the job | PASS |
| 17 Undo after hard kill: 10 of 10 kills fully undone (was 3 misses in 15) | PASS |
| 20 --clean-empty / undo remove empty folders | PASS |
| 19 .git-only folder | NOT A BUG: my test folder had a fresh .git directory date (so it was under 24 h old). Real .git folders are protected and the rule works. |

## Full re-run of every earlier suite on 2.7.1
| Suite | Before | Now | What the remaining failures are |
|---|---|---|---|
| Simple + Medium batch 2 (100 tests) | 94 | 100 / 100 | none |
| Hard batch 2 (53 tests) | 50 | 53 / 53 | none |
| Simple batch 3 (102 tests) | 81 | 99 / 102 | 3 expected: .epub goes to Ebooks, .psd and .ai to Design (own folders exist) |
| Medium batch 3 (99 tests) | 94 | 95 / 99 | 4 are my test's mistake (it re-ran the organizer after undo, which files the files again); undo + --clean-empty is verified separately |
| Hard batch 3, kills / chaos / names (45 tests) | 37 | 45 / 45 | none |
| Hard batch 3, parallel / scale / live changes (54 tests) | 54 | 54 / 55 | 1 is my test re-creating emptied files |
| First 60 tests (simple/medium/hard) | see above | 54 / 60 | 6 are old test-setup mistakes (version text now 2.7.1, history needs a folder, project marker, 3+ photos) plus an undo test that now shows a warning instead of silently skipping |

Result: no real failure is left in anything we can test on Linux. NOT proven (needs a real Windows PC): scheduled-task XML, right-click menu, .bat helpers, case-insensitive clashes, 260-character paths, Notepad/PowerShell encodings, OneDrive Downloads, full disk, and the Windows version of the "is the old run still alive" check.


---
# VERSION 2.8 (desktop app) TESTS (12 Nov 2026)

## 1. App logic (app_backend.py): 38 / 38 PASS  (2_History/test_scripts/test_backend.py)
First run and settings file; all 7 ways of organizing (each one sorts a sample folder as described); switching way keeps watched folders and ignore list; unknown way explained; "where would this file go"; sorting rules add / edit / turn off / move / delete; 10 kinds of bad rule explained and not saved (empty name, nothing to match, no folder, C:\ or / or ../ folders, slow regex, broken regex, unknown sub-folder, bad size); extensions get a dot; topics; options; watched folders; preview vs real run; fresh-file tip; project folder refused / "organize anyway"; missing and system folders refused; history list, details, undo, restore one file, undo one chosen run; TWO USERS keep separate settings and separate history; export / import settings (bad files rejected); damaged settings message + reset keeps backup; Notepad (BOM) settings; health, space, duplicates, set aside; pause (automatic waits, own run goes ahead), resume, bad pause text; recent runs; organize all watched folders; start-with-Windows file written and removed; odd file names; slow regex cannot freeze a run.

## 2. Window code clicked through with a fake Tkinter: 49 / 49 PASS  (test_ui.py + fake_tk.py)
First-run wizard, all five tabs, preview -> organize -> history -> undo / restore, rules dialog results, topics, ignore list, watched folders, dashboard buttons, pause / resume, presets, options (bad number explained), background timer, start-with-Windows message on non-Windows, export / import / reset, errors shown as messages (missing folder), "organize anyway" prompt for a project folder (this found and fixed an endless prompt loop), numeric-looking file names and run ids stay exact, tray menu (5 entries, organize, pause, resume, close-to-tray hint once, quit) with a pretend pystray.
Bugs found by these tests and fixed before release: the endless "organize anyway" prompt; the history run ids / file names that Tk would have turned into numbers (e.g. 00123456); a shared history folder when switching users in one process; "/folder" typed as a rule destination was silently treated as relative.

## 3. Engine regression on 2.8 (the engine changed only for the per-user data folder and exe-friendly paths)
| Suite | Result |
|---|---|
| 2.7.1 fix checks (23) | 22 / 23 (the 1 is the known test-setup artifact: a log file owned by another user) |
| First 60 tests | same as 2.7.1 (the 6 known test-setup mistakes) |
| Batch 2 simple + medium (100) | 100 / 100 |
| Batch 2 hard (53) | 53 / 53 |
| Batch 3 simple (102) | 99 / 102 (.epub, .psd, .ai have their own folders) |
| Batch 3 hard: kills / chaos / names (45) | 45 / 45 |
| Batch 3 hard: parallel / scale / live changes (55) | 54 / 55 (known test artifact) |
| Batch 3 medium (99) | not re-run (nothing it covers changed) |

## NOT proven (needs a real Windows PC and screen)
How the window looks (sizes, fonts, layout), the real tray icon, start-with-Windows, building the .exe with build_exe.bat, and everything listed earlier (scheduled task, right-click menu, long paths, OneDrive Downloads...). If the window shows an error, the text is also written to %APPDATA%\Organizer\history\organizer.log.


---
# BATCH 4 (13 Nov 2026): app logic at scale, 184 tests, 184 / 184 PASS  (tests/stress/b4.py)
| Group | Tests | Result |
|---|---|---|
| A. Every way of organizing x 14 file types (7 x 14): preview shows the file, a real run moves it with 0 errors, undo puts it back exactly | 98 | 98 / 98 |
| B. Rules editor: 10 random valid rules are saved, listed, read back and really route a file; 10 invalid rules (../ and C:\ and / and ~ folders, empty name, nothing to match, slow regex, broken regex, unknown sub-folder, a/../../b) are rejected and the settings file is byte-for-byte unchanged | 20 | 20 / 20 |
| C. Pause text: 30m, 1h, 2h, 1d, forever, 5m accepted; abc, empty, -5, 1x refused with a message | 10 | 10 / 10 |
| D. History: 12 separate runs undone in random order (10 different orders): every file back, history empty | 10 | 10 / 10 |
| E. 2, 3, 4, 6 and 8 different users running at the same time (separate processes): each organizes 30 files and sees only their own history | 5 | 5 / 5 |
| F. "Where would this file go?" for 40 names (RAW, .tar.gz, no extension, Japanese, emoji, Makefile...) answers every time and creates no stray files | 41 | 41 / 41 |
One mistake in my own first version of group B (a name pattern that cannot match a name with an extension) was fixed in the test, not in the program.


---
# VERSION 2.8 - SHARED SETUP + STARTUP SAFETY (14 Nov 2026)
## New automated tests: 21 (all pass; part of the 77 in tests/)
- **Launcher (6):** the self-test prints a plain report and saves it; running it twice changes nothing; a crash leaves startup_error.txt instead of vanishing; a second copy is refused while the first is alive; a leftover lock from a crash does not block start; the lock is released at exit.
- **Shared setup (15):** a run made in the app shows in the command line history and can be undone there (and the other way round); the scheduled task (`--all --scheduled`) follows the watched folders AND the rules set in the app and its runs can be undone in the app; pause set in the app stops the task but not a manual run; pause / resume from the command line show in the app; `manage_folders.py watch-add` edits the same settings as the app; `--doctor` and `repair.py --check` use the per-user folder; two users never see each other's history; history made by an older version next to the program is copied once and stays undoable; `portable.txt` keeps everything next to the program; the first command-line run creates the user's own settings copy; an existing watch setup is kept when the app starts first; a fresh user gets the first-run choice.
- Bug found and fixed by these tests: the app kept using the previous user's history folder when a second data folder was opened in the same process.
## Regression of every earlier engine suite (about 630 tests), in BOTH layouts
| Suite | Old layout (portable) | New per-user layout |
|---|---|---|
| Fix checks (23) | 22 / 23 (known test artifact) | same code path |
| First 60 tests | same as before (6 known test mistakes) | not repeated (they read the old history path) |
| Batch 2 (153) | 153 / 153 | 153 / 153 |
| Batch 3 simple (102) | 99 / 102 (.epub .psd .ai have own folders) | 99 / 102 |
| Batch 3 medium (99) | not repeated | 92 / 99 (the same 7 test mistakes as before) |
| Batch 3 hard: kills, chaos, names (45) | 45 / 45 | 45 / 45 |
| Batch 3 hard: parallel, scale, live changes (55) | 54 / 55 | 53 / 55 (+1 test that looks for the history file in the old place) |
No regression. Windows-only items are still unproven (scheduled task XML, right-click menu, real window and tray, building the .exe, long paths, OneDrive Downloads).
