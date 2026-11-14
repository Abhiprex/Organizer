Test scripts used for Organizer 2.7-2.8 (Python 3, Linux sandbox).
They create synthetic folders in /tmp and expect the program copy in /tmp/nbXXX (set PK=/path/to/1_Project copy).
big/b2a/b2b/b3*: engine suites (simple, medium, hard). verify.py: one check per 2.7.1 fix.
test_backend.py: app_backend tests. test_ui.py + fake_tk.py: click-through of the window code with a fake Tkinter.
Paths such as /home/claude/... may need changing on another machine.
