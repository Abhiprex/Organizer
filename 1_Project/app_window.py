"""
Organizer 2.8 - app_window.py: the desktop window (started by organizer_app.py / app.bat).

Tabs: Organize (preview, then organize), History (undo / restore), My Rules (sorting rules, topics, ignore list,
watched folders), Dashboard (health, space, duplicates, pause), Settings (ways of organizing, options, sharing).
With  pip install pystray pillow  it also lives in the system tray and can organize in the background.
All the real work is done by app_backend.py / organizer.py; this file only shows things and collects choices.
"""
import os
import queue
import sys
import threading
import traceback
from pathlib import Path

import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, ttk

import app_backend as ab

try:                                       # optional: the tray icon
    import pystray
    from PIL import Image, ImageDraw
    HAVE_TRAY = True
except Exception:                          # not installed: the app simply works as a normal window
    HAVE_TRAY = False

TITLE = "Organizer 2.8"
SUBFOLDER_CHOICES = [("extension", "by file type (PDF, JPG...)"), ("year", "by year"), ("month", "by month"),
                     ("year-month", "by year, then month"), ("first-letter", "by first letter"),
                     ("size", "by size"), ("topic", "by topic words")]


def split_list(text):
    return [part.strip() for part in text.replace(";", ",").split(",") if part.strip()]


class RuleDialog(tk.Toplevel):
    """Add or edit one sorting rule."""

    def __init__(self, parent, backend, rule=None):
        super().__init__(parent)
        self.backend, self.result = backend, None
        self.title("Sorting rule")
        self.resizable(False, False)
        self.transient(parent)
        rule = rule or {}
        self.vars = {
            "name": tk.StringVar(value=rule.get("name", "")),
            "extensions": tk.StringVar(value=", ".join(rule.get("extensions", []))),
            "patterns": tk.StringVar(value=", ".join(rule.get("patterns", []))),
            "regex": tk.StringVar(value=rule.get("regex", "")),
            "min_size_mb": tk.StringVar(value=str(rule.get("min_size_mb", ""))),
            "max_size_mb": tk.StringVar(value=str(rule.get("max_size_mb", ""))),
            "dest": tk.StringVar(value=rule.get("dest", "")),
        }
        labels = [("name", "Name of the rule"), ("extensions", "File types  (pdf, docx, jpg ...)"),
                  ("patterns", "Name contains / matches  (invoice*, *final* ...)"),
                  ("regex", "Advanced: pattern (regex)"), ("min_size_mb", "Bigger than (MB)"),
                  ("max_size_mb", "Smaller than (MB)"), ("dest", "Goes to folder  (e.g. Money/Invoices)")]
        form = ttk.Frame(self, padding=12)
        form.grid(sticky="nsew")
        for row, (key, text) in enumerate(labels):
            ttk.Label(form, text=text).grid(row=row, column=0, sticky="w", pady=3)
            ttk.Entry(form, textvariable=self.vars[key], width=42).grid(row=row, column=1, pady=3, padx=6)
        ttk.Label(form, text="Then sort inside it").grid(row=len(labels), column=0, sticky="nw", pady=3)
        box = ttk.Frame(form)
        box.grid(row=len(labels), column=1, sticky="w")
        self.mode_vars = {}
        have = rule.get("subfolders", [])
        for i, (mode, text) in enumerate(SUBFOLDER_CHOICES):
            self.mode_vars[mode] = tk.BooleanVar(value=mode in have)
            ttk.Checkbutton(box, text=text, variable=self.mode_vars[mode]).grid(row=i, column=0, sticky="w")
        self.enabled = tk.BooleanVar(value=rule.get("enabled", True) is not False)
        ttk.Checkbutton(form, text="Rule is on", variable=self.enabled).grid(row=len(labels) + 1, column=1, sticky="w")
        buttons = ttk.Frame(form)
        buttons.grid(row=len(labels) + 2, column=1, sticky="e", pady=8)
        ttk.Button(buttons, text="Cancel", command=self.destroy).grid(row=0, column=0, padx=4)
        ttk.Button(buttons, text="Save", command=self.save).grid(row=0, column=1)
        self.grab_set()

    def save(self):
        rule = {"name": self.vars["name"].get(), "extensions": split_list(self.vars["extensions"].get()),
                "patterns": split_list(self.vars["patterns"].get()), "regex": self.vars["regex"].get(),
                "min_size_mb": self.vars["min_size_mb"].get().strip(), "max_size_mb": self.vars["max_size_mb"].get().strip(),
                "dest": self.vars["dest"].get(),
                "subfolders": [m for m, v in self.mode_vars.items() if v.get()],
                "enabled": bool(self.enabled.get())}
        try:
            self.result = self.backend.clean_rule(rule)
        except ab.BackendError as exc:
            messagebox.showerror(TITLE, str(exc), parent=self)
            return
        self.destroy()


class App:
    def __init__(self, start_hidden=False):
        self.backend = ab.Backend()
        self.root = tk.Tk()
        self.root.title(TITLE)
        width = min(1020, max(640, int(self.root.winfo_screenwidth()) - 80))
        height = min(680, max(480, int(self.root.winfo_screenheight()) - 120))
        self.root.geometry(f"{width}x{height}")
        self.root.minsize(min(860, width), min(560, height))
        style = ttk.Style()
        for theme in ("vista", "clam"):
            if theme in style.theme_names():
                style.theme_use(theme)
                break
        self.q = queue.Queue()
        self.watch_combos = []
        self.tray = None
        self._auto_job = None
        self._busy = 0
        settings = self.backend.app_settings()
        start = settings.get("last_folder") or str(Path.home() / "Downloads")
        self.folder_var = tk.StringVar(value=start)
        self.status = tk.StringVar(value="Ready.")
        self._build()
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        self.root.after(250, self._poll)
        if self.backend.first_run and not settings.get("first_run_done"):
            self.root.after(400, self.first_run_wizard)
        self._start_tray()
        self._schedule_auto()
        if start_hidden and self.tray:
            self.root.withdraw()

    # ---------------------------------------------------------------- plumbing
    def _poll(self):
        try:
            while True:
                self.q.get_nowait()()
        except queue.Empty:
            pass
        self.root.after(250, self._poll)

    def bg(self, work, done, message="Working..."):
        """Run work() off the screen thread; done(result, error) runs back on the screen thread."""
        self._busy += 1
        self.status.set(message)
        self.progress.start(12)

        def runner():
            result = error = None
            try:
                result = work()
            except Exception as exc:                           # shown to the user, never a silent crash
                error = exc
                if not isinstance(exc, ab.BackendError):
                    ab.organizer.log.error("app error: %s", traceback.format_exc())
            self.q.put(lambda: self._finish(done, result, error))
        threading.Thread(target=runner, daemon=True).start()

    def _finish(self, done, result, error):
        self._busy -= 1
        if self._busy <= 0:
            self.progress.stop()
        try:
            done(result, error)
        except Exception as exc:
            self.show_error(exc)

    def show_error(self, exc):
        if isinstance(exc, ab.BackendError):
            messagebox.showwarning(TITLE, str(exc))
        else:
            messagebox.showerror(TITLE, f"Something unexpected happened:\n{exc}\n\nDetails are in the log "
                                        f"({self.backend.data_dir / 'history' / 'organizer.log'}).")
        self.status.set("Stopped.")

    def folder(self):
        return self.folder_var.get().strip()

    def remember_folder(self):
        self.backend.set_app_settings(last_folder=self.folder())

    @staticmethod
    def fill(tree, rows, iids=None):
        """Show rows. Tk turns text like 00123456 into the number 123456, so ids and names that must stay
        exact are also kept as the row's id (iids) and read back from there."""
        tree.delete(*tree.get_children())
        for i, values in enumerate(rows):
            if iids is not None:
                tree.insert("", "end", iid=str(iids[i]), values=values)
            else:
                tree.insert("", "end", values=values)

    def folder_bar(self, parent):
        bar = ttk.Frame(parent)
        ttk.Label(bar, text="Folder:").grid(row=0, column=0, padx=(0, 6))
        ttk.Entry(bar, textvariable=self.folder_var, width=60).grid(row=0, column=1, sticky="ew")
        ttk.Button(bar, text="Browse...", command=self.browse).grid(row=0, column=2, padx=6)
        combo = ttk.Combobox(bar, values=self.backend.get_watch(), width=26, state="readonly")
        combo.grid(row=0, column=3)
        combo.bind("<<ComboboxSelected>>", lambda e, c=combo: self.folder_var.set(c.get()))
        self.watch_combos.append(combo)
        bar.columnconfigure(1, weight=1)
        return bar

    def browse(self):
        chosen = filedialog.askdirectory(initialdir=self.folder() or str(Path.home()))
        if chosen:
            self.folder_var.set(chosen)
            self.remember_folder()

    # ---------------------------------------------------------------- layout
    def _build(self):
        top = ttk.Frame(self.root)
        top.pack(fill="both", expand=True)
        self.notebook = ttk.Notebook(top)
        self.notebook.pack(fill="both", expand=True, padx=8, pady=(8, 0))
        tabs = [("Organize", self._tab_organize), ("History", self._tab_history), ("My Rules", self._tab_rules),
                ("Dashboard", self._tab_dashboard), ("Settings", self._tab_settings)]
        bottom = ttk.Frame(self.root)
        bottom.pack(fill="x", padx=8, pady=6)
        ttk.Label(bottom, textvariable=self.status).pack(side="left")
        self.progress = ttk.Progressbar(bottom, mode="indeterminate", length=140)
        self.progress.pack(side="right")
        for title, builder in tabs:
            frame = ttk.Frame(self.notebook, padding=10)
            self.notebook.add(frame, text=title)
            builder(frame)
        self.notebook.bind("<<NotebookTabChanged>>", self._tab_changed)

    def _tab_changed(self, _event=None):
        index = self.notebook.index(self.notebook.select())
        if index == 1:
            self.refresh_history()
        elif index == 2:
            self.refresh_rules()
        elif index == 3:
            self.refresh_dashboard()
        elif index == 4:
            self.refresh_settings()

    # ---------------------------------------------------------------- Organize tab
    def _tab_organize(self, tab):
        self.folder_bar(tab).pack(fill="x")
        options = ttk.Frame(tab)
        options.pack(fill="x", pady=6)
        self.include_new = tk.BooleanVar(value=False)
        self.recursive = tk.BooleanVar(value=False)
        ttk.Checkbutton(options, text="Include files from the last 30 seconds", variable=self.include_new).pack(side="left")
        ttk.Checkbutton(options, text="Include sub-folders", variable=self.recursive).pack(side="left", padx=12)
        ttk.Button(options, text="Organize now", command=self.organize_clicked).pack(side="right")
        ttk.Button(options, text="Preview (moves nothing)", command=self.preview_clicked).pack(side="right", padx=6)
        self.plan_tree = self._tree(tab, ("File", "Goes to", "Because of rule"), (330, 380, 200))
        self.plan_note = tk.StringVar(value="Press Preview to see what would happen. Nothing moves until you press Organize now.")
        ttk.Label(tab, textvariable=self.plan_note, wraplength=900).pack(fill="x", pady=4)
        self.undo_last_btn = ttk.Button(tab, text="Undo the last run in this folder", command=self.undo_last)
        self.undo_last_btn.pack(anchor="e")

    def _tree(self, parent, columns, widths, height=12):
        frame = ttk.Frame(parent)
        frame.pack(fill="both", expand=True)
        tree = ttk.Treeview(frame, columns=columns, show="headings", height=height)
        for col, width in zip(columns, widths):
            tree.heading(col, text=col)
            tree.column(col, width=width, anchor="w")
        scroll = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=scroll.set)
        tree.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")
        return tree

    def _run_args(self):
        return dict(include_new=bool(self.include_new.get()), recursive=True if self.recursive.get() else None)

    def preview_clicked(self, force=False):
        self.remember_folder()
        self.bg(lambda: self.backend.run(self.folder(), dry_run=True, force=force, **self._run_args()),
                lambda r, e: self._preview_done(r, e, force), "Looking at the folder...")

    def _preview_done(self, result, error, forced=False):
        if error:
            return self._maybe_force(error, lambda: self.preview_clicked(force=True), forced)
        self.fill(self.plan_tree, [(p["name"], p["dest"], p["rule"]) for p in result["plan"]])
        n = len(result["plan"])
        self.plan_note.set(f"{n} file(s) would be moved. Nothing has been changed yet." if n else
                           "Nothing to organize right now (files may be too new, ignored, or already in place).")
        self.status.set("Preview ready.")

    def _maybe_force(self, error, retry, forced=False):
        """A project / home folder is refused unless the user says 'organize anyway' (never for system folders)."""
        if not forced and isinstance(error, ab.BackendError) and error.kind == "unsafe":
            if messagebox.askyesno(TITLE, f"{error}\n\nOrganize this folder anyway?"):
                retry()
                return
        self.show_error(error)

    def organize_clicked(self, force=False):
        self.remember_folder()

        def after_preview(result, error):
            if error:
                return self._maybe_force(error, lambda: self.organize_clicked(force=True), force)
            n = len(result["plan"])
            self.fill(self.plan_tree, [(p["name"], p["dest"], p["rule"]) for p in result["plan"]])
            if not n:
                self.plan_note.set("Nothing to organize right now.")
                self.status.set("Nothing to do.")
                return
            if not messagebox.askyesno(TITLE, f"Move {n} file(s) now?\nYou can undo this afterwards."):
                self.status.set("Cancelled.")
                return
            self.bg(lambda: self.backend.run(self.folder(), dry_run=False, force=force, **self._run_args()),
                    self._organize_done, "Organizing...")
        self.bg(lambda: self.backend.run(self.folder(), dry_run=True, force=force, **self._run_args()), after_preview,
                "Checking first...")

    def _organize_done(self, result, error):
        if error:
            return self.show_error(error)
        if result["status"] == "busy":
            self.plan_note.set("Another run is already working on this folder. Try again in a moment.")
        else:
            s = result["stats"]
            self.plan_note.set(f"Done: {s.get('moved', 0)} moved, {s.get('skipped', 0)} skipped, {s.get('errors', 0)} problem(s). "
                               f"You can undo this from the History tab.")
        self.status.set("Done.")

    def undo_last(self):
        if not messagebox.askyesno(TITLE, "Undo the last organizing run in this folder?"):
            return
        self.bg(lambda: self.backend.undo(self.folder()), lambda r, e: self.show_error(e) if e else
                (self.plan_note.set(r[-1] if r else "Nothing to undo."), self.status.set("Undone.")), "Undoing...")

    # ---------------------------------------------------------------- History tab
    def _tab_history(self, tab):
        self.folder_bar(tab).pack(fill="x")
        ttk.Label(tab, text="Runs in this folder (newest first). Select one to see its files.").pack(anchor="w", pady=(8, 2))
        self.runs_tree = self._tree(tab, ("Run", "When", "Files", "Examples"), (90, 150, 60, 560), 6)
        self.runs_tree.bind("<<TreeviewSelect>>", lambda e: self.show_run_items())
        self.items_tree = self._tree(tab, ("File", "Was in", "Now in"), (260, 330, 330), 8)
        bar = ttk.Frame(tab)
        bar.pack(fill="x", pady=6)
        ttk.Button(bar, text="Refresh", command=self.refresh_history).pack(side="left")
        ttk.Button(bar, text="Undo the selected run", command=self.undo_selected_run).pack(side="right")
        ttk.Button(bar, text="Put the selected file(s) back", command=self.restore_selected).pack(side="right", padx=6)

    def refresh_history(self):
        if not self.folder():
            return
        self.bg(lambda: self.backend.history(self.folder()), self._history_done, "Reading history...")

    def _history_done(self, rows, error):
        if error:
            return self.show_error(error)
        self.fill(self.runs_tree, [(r["run"], r["time"], r["count"], r["examples"]) for r in rows],
                  iids=[r["run"] for r in rows])
        self.fill(self.items_tree, [])
        self.status.set(f"{len(rows)} run(s) recorded." if rows else "No runs recorded for this folder yet.")

    def _selected_run(self):
        sel = self.runs_tree.selection()
        return str(sel[0]) if sel else None

    def show_run_items(self):
        run = self._selected_run()
        if run is None:
            return
        self.bg(lambda: self.backend.history_items(self.folder(), str(run)),
                lambda rows, e: self.show_error(e) if e else self._show_items(rows), "Loading files...")

    def _show_items(self, rows):
        self.fill(self.items_tree, [(r["name"], r["from"], r["to"]) for r in rows], iids=[f"i{n}" for n in range(len(rows))])
        self._item_names = {f"i{n}": r["name"] for n, r in enumerate(rows)}

    def undo_selected_run(self):
        run = self._selected_run()
        if run is None:
            return messagebox.showinfo(TITLE, "Select a run first.")
        if not messagebox.askyesno(TITLE, f"Undo run {run}? Its files go back to where they were."):
            return
        self.bg(lambda: self.backend.undo(self.folder(), str(run)),
                lambda r, e: self.show_error(e) if e else (self.status.set(r[-1] if r else "Undone."), self.refresh_history()),
                "Undoing...")

    def restore_selected(self):
        names = [getattr(self, "_item_names", {}).get(i) for i in self.items_tree.selection()]
        names = [n for n in names if n]
        if not names:
            return messagebox.showinfo(TITLE, "Select one or more files in the lower list first.")
        self.bg(lambda: self.backend.restore(self.folder(), [str(n) for n in names]),
                lambda r, e: self.show_error(e) if e else (self.status.set(r[-1] if r else "Done."), self.refresh_history()),
                "Putting files back...")

    # ---------------------------------------------------------------- My Rules tab
    def _tab_rules(self, tab):
        sub = ttk.Notebook(tab)
        sub.pack(fill="both", expand=True)
        for title, builder in (("Sorting rules", self._rules_sorting), ("Topics", self._rules_topics),
                               ("Ignore list", self._rules_ignore), ("Watched folders", self._rules_watch)):
            frame = ttk.Frame(sub, padding=8)
            sub.add(frame, text=title)
            builder(frame)

    def _rules_sorting(self, tab):
        ttk.Label(tab, text="The first rule that matches a file wins. New rules go to the top. "
                            "Folders are always inside the folder being organized.", wraplength=900).pack(anchor="w")
        self.rules_tree = self._tree(tab, ("On", "Name", "Files", "Goes to", "Sorted by"), (40, 160, 340, 200, 170), 10)
        bar = ttk.Frame(tab)
        bar.pack(fill="x", pady=6)
        for text, command in (("Add rule...", self.rule_add), ("Edit...", self.rule_edit), ("Delete", self.rule_delete),
                              ("Move up", lambda: self.rule_move(-1)), ("Move down", lambda: self.rule_move(1)),
                              ("Turn on / off", self.rule_toggle)):
            ttk.Button(bar, text=text, command=command).pack(side="left", padx=2)
        test = ttk.Frame(tab)
        test.pack(fill="x", pady=8)
        ttk.Label(test, text="Where would a file go?").pack(side="left")
        self.test_name = tk.StringVar()
        ttk.Entry(test, textvariable=self.test_name, width=34).pack(side="left", padx=6)
        ttk.Button(test, text="Check", command=self.rule_test).pack(side="left")
        self.test_result = tk.StringVar()
        ttk.Label(test, textvariable=self.test_result).pack(side="left", padx=10)

    def refresh_rules(self):
        try:
            rows = self.backend.rule_rows()
            topics = self.backend.get_topics()
            ignore = self.backend.get_ignore()
            watch = self.backend.get_watch()
        except ab.BackendError as exc:
            return self.show_error(exc)
        self.fill(self.rules_tree, [("yes" if r["enabled"] else "no", r["name"], r["what"], r["dest"], r["subfolders"]) for r in rows])
        self.fill(self.topics_tree, [(name, ", ".join(words)) for name, words in topics.items()], iids=list(topics))
        self.ignore_list.delete(0, "end")
        for item in ignore:
            self.ignore_list.insert("end", item)
        self.watch_list.delete(0, "end")
        for item in watch:
            self.watch_list.insert("end", item)
        for combo in self.watch_combos:
            combo.configure(values=watch)

    def _rule_index(self):
        sel = self.rules_tree.selection()
        if not sel:
            messagebox.showinfo(TITLE, "Select a rule first.")
            return None
        return self.rules_tree.get_children().index(sel[0]) if hasattr(self.rules_tree.get_children(), "index") else 0

    def _rule_action(self, fn):
        try:
            fn()
        except (ab.BackendError, IndexError) as exc:
            self.show_error(exc if isinstance(exc, ab.BackendError) else ab.BackendError("Select a rule first."))
        self.refresh_rules()

    def rule_add(self):
        dialog = RuleDialog(self.root, self.backend)
        self.root.wait_window(dialog)
        if dialog.result:
            dialog.result.pop("custom", None)
            self._rule_action(lambda: self.backend.add_rule(dialog.result))

    def rule_edit(self):
        index = self._rule_index()
        if index is None:
            return
        dialog = RuleDialog(self.root, self.backend, self.backend.get_rule(index))
        self.root.wait_window(dialog)
        if dialog.result:
            self._rule_action(lambda: self.backend.update_rule(index, dialog.result))

    def rule_delete(self):
        index = self._rule_index()
        if index is not None and messagebox.askyesno(TITLE, "Delete this rule? (You can always switch back to a ready-made way in Settings.)"):
            self._rule_action(lambda: self.backend.delete_rule(index))

    def rule_move(self, delta):
        index = self._rule_index()
        if index is not None:
            self._rule_action(lambda: self.backend.move_rule(index, delta))

    def rule_toggle(self):
        index = self._rule_index()
        if index is not None:
            on = self.backend.rule_rows()[index]["enabled"]
            self._rule_action(lambda: self.backend.set_rule_enabled(index, not on))

    def rule_test(self):
        try:
            dest, label = self.backend.where_would_go(self.test_name.get())
            self.test_result.set(f"goes to  {dest}   (rule: {label})" if dest else "stays where it is")
        except ab.BackendError as exc:
            self.show_error(exc)

    def _rules_topics(self, tab):
        ttk.Label(tab, text="Topics group files by words in their names, e.g. Taxes = tax, gst. "
                            "They are used by rules that sort 'by topic words'.", wraplength=900).pack(anchor="w")
        self.topics_tree = self._tree(tab, ("Topic", "Words"), (200, 700), 10)
        bar = ttk.Frame(tab)
        bar.pack(fill="x", pady=6)
        ttk.Button(bar, text="Add / change topic...", command=self.topic_edit).pack(side="left", padx=2)
        ttk.Button(bar, text="Delete topic", command=self.topic_delete).pack(side="left", padx=2)

    def topic_edit(self):
        sel = self.topics_tree.selection()
        name0 = str(sel[0]) if sel else ""
        name = simpledialog.askstring(TITLE, "Topic name:", initialvalue=name0)
        if not name:
            return
        topics = self.backend.get_topics()
        words = simpledialog.askstring(TITLE, "Words that belong to it (separate with commas):",
                                       initialvalue=", ".join(topics.get(name, [])))
        if words is None:
            return
        topics[name.strip()] = split_list(words)
        self._rule_action(lambda: self.backend.set_topics(topics))

    def topic_delete(self):
        sel = self.topics_tree.selection()
        if not sel:
            return
        topics = self.backend.get_topics()
        topics.pop(str(sel[0]), None)
        self._rule_action(lambda: self.backend.set_topics(topics))

    def _list_editor(self, tab, hint, add_text, add_cmd, remove_cmd):
        ttk.Label(tab, text=hint, wraplength=900).pack(anchor="w")
        box = tk.Listbox(tab, height=12)
        box.pack(fill="both", expand=True, pady=6)
        bar = ttk.Frame(tab)
        bar.pack(fill="x")
        ttk.Button(bar, text=add_text, command=add_cmd).pack(side="left", padx=2)
        ttk.Button(bar, text="Remove selected", command=remove_cmd).pack(side="left", padx=2)
        return box

    def _rules_ignore(self, tab):
        self.ignore_list = self._list_editor(tab, "Files whose names match these patterns are never touched (for example  *.log  or  secret*).",
                                             "Add pattern...", self.ignore_add, self.ignore_remove)

    def ignore_add(self):
        text = simpledialog.askstring(TITLE, "Name pattern to leave alone (for example *.log):")
        if text:
            self._rule_action(lambda: self.backend.set_ignore(self.backend.get_ignore() + [text]))

    def ignore_remove(self):
        sel = self.ignore_list.curselection()
        if sel:
            current = self.backend.get_ignore()
            del current[sel[0]]
            self._rule_action(lambda: self.backend.set_ignore(current))

    def _rules_watch(self, tab):
        self.watch_list = self._list_editor(tab, "Folders that the tray / scheduled runs keep tidy (for example Downloads).",
                                            "Add folder...", self.watch_add, self.watch_remove)

    def watch_add(self):
        chosen = filedialog.askdirectory(initialdir=str(Path.home()))
        if chosen:
            self._rule_action(lambda: self.backend.add_watch(chosen))

    def watch_remove(self):
        sel = self.watch_list.curselection()
        if sel:
            path = self.watch_list.get(sel[0])
            self._rule_action(lambda: self.backend.remove_watch(path))

    # ---------------------------------------------------------------- Dashboard tab
    def _tab_dashboard(self, tab):
        self.folder_bar(tab).pack(fill="x")
        bar = ttk.Frame(tab)
        bar.pack(fill="x", pady=6)
        for text, command in (("Health check", self.dash_health), ("Space report", self.dash_space),
                              ("Find duplicates", self.dash_dupes), ("Set duplicates aside...", self.dash_aside)):
            ttk.Button(bar, text=text, command=command).pack(side="left", padx=2)
        self.report = tk.Text(tab, height=14, wrap="word", font=("Consolas", 10))
        self.report.pack(fill="both", expand=True)
        pause = ttk.Frame(tab)
        pause.pack(fill="x", pady=6)
        ttk.Label(pause, text="Pause automatic organizing for").pack(side="left")
        self.pause_choice = ttk.Combobox(pause, values=["30m", "1h", "2h", "4h", "1d", "forever"], width=8, state="readonly")
        self.pause_choice.set("1h")
        self.pause_choice.pack(side="left", padx=6)
        ttk.Button(pause, text="Pause", command=self.dash_pause).pack(side="left")
        ttk.Button(pause, text="Resume", command=self.dash_resume).pack(side="left", padx=6)
        self.pause_label = tk.StringVar()
        ttk.Label(pause, textvariable=self.pause_label).pack(side="left", padx=10)
        self.recent_tree = self._tree(tab, ("When", "Folder", "Moved", "Result"), (160, 450, 80, 200), 5)

    def show_report(self, text):
        self.report.delete("1.0", "end")
        self.report.insert("end", text.strip() or "(nothing to report)")

    def refresh_dashboard(self):
        try:
            status = self.backend.pause_status()
            recent = self.backend.recent_runs()
        except ab.BackendError as exc:
            return self.show_error(exc)
        self.pause_label.set(f"Paused {status}." if status else "Automatic organizing is on.")
        self.fill(self.recent_tree, [(r.get("time", "")[:16].replace("T", " "), r.get("folder", ""), r.get("moved", ""),
                                      r.get("status", "")) for r in recent])

    def _report_job(self, work, message):
        self.bg(work, lambda r, e: self.show_error(e) if e else self.show_report(r if isinstance(r, str) else r[0]), message)

    def dash_health(self):
        self._report_job(self.backend.health_text, "Checking health...")

    def dash_space(self):
        self._report_job(lambda: self.backend.space_text(self.folder()), "Measuring space...")

    def dash_dupes(self):
        self._report_job(lambda: self.backend.duplicates_text(self.folder()), "Looking for duplicates...")

    def dash_aside(self):
        if messagebox.askyesno(TITLE, "Move extra copies of identical files into a _Duplicates folder?\n"
                                      "One copy of each stays where it is. Nothing is deleted."):
            self._report_job(lambda: self.backend.set_aside_duplicates(self.folder()), "Setting duplicates aside...")

    def dash_pause(self):
        self._rule_dash(lambda: self.backend.snooze(self.pause_choice.get()))

    def dash_resume(self):
        self._rule_dash(self.backend.resume)

    def _rule_dash(self, fn):
        try:
            self.status.set(fn() or "Done.")
        except ab.BackendError as exc:
            self.show_error(exc)
        self.refresh_dashboard()

    # ---------------------------------------------------------------- Settings tab
    def _tab_settings(self, tab):
        box = ttk.LabelFrame(tab, text="Way of organizing", padding=8)
        box.pack(fill="x")
        self.preset_label = tk.StringVar()
        ttk.Label(box, textvariable=self.preset_label, font=("Segoe UI", 10, "bold")).pack(anchor="w")
        self.presets = self.backend.list_presets()
        self.preset_combo = ttk.Combobox(box, values=[p["name"] for p in self.presets], state="readonly", width=34)
        self.preset_combo.pack(anchor="w", pady=4)
        self.preset_combo.bind("<<ComboboxSelected>>", lambda e: self.show_preset_text())
        self.preset_text = tk.StringVar()
        ttk.Label(box, textvariable=self.preset_text, wraplength=880).pack(anchor="w")
        ttk.Button(box, text="Use this way of organizing", command=self.apply_preset).pack(anchor="w", pady=4)
        opt = ttk.LabelFrame(tab, text="Options", padding=8)
        opt.pack(fill="x", pady=8)
        self.opt_conflict = ttk.Combobox(opt, values=["rename", "skip", "overwrite"], width=10, state="readonly")
        self.opt_age = tk.StringVar()
        self.opt_recursive = tk.BooleanVar()
        self.opt_dedupe = tk.BooleanVar()
        ttk.Label(opt, text="If a file with the same name is already there:").grid(row=0, column=0, sticky="w")
        self.opt_conflict.grid(row=0, column=1, padx=6, sticky="w")
        ttk.Label(opt, text="(rename keeps both - safest)").grid(row=0, column=2, sticky="w")
        ttk.Label(opt, text="Leave files alone until they are this old (seconds):").grid(row=1, column=0, sticky="w")
        ttk.Entry(opt, textvariable=self.opt_age, width=8).grid(row=1, column=1, padx=6, sticky="w")
        ttk.Checkbutton(opt, text="Also organize files inside sub-folders", variable=self.opt_recursive).grid(row=2, column=0, sticky="w")
        ttk.Checkbutton(opt, text="Set identical copies aside as duplicates", variable=self.opt_dedupe).grid(row=3, column=0, sticky="w")
        ttk.Button(opt, text="Save options", command=self.save_options).grid(row=4, column=0, sticky="w", pady=6)
        bg = ttk.LabelFrame(tab, text="In the background", padding=8)
        bg.pack(fill="x")
        self.auto_var = tk.BooleanVar()
        self.auto_minutes = tk.StringVar()
        self.startup_var = tk.BooleanVar()
        ttk.Checkbutton(bg, text="Keep my watched folders tidy while this app is running, every", variable=self.auto_var,
                        command=self.save_auto).grid(row=0, column=0, sticky="w")
        ttk.Entry(bg, textvariable=self.auto_minutes, width=5).grid(row=0, column=1, padx=4)
        ttk.Label(bg, text="minutes").grid(row=0, column=2, sticky="w")
        ttk.Checkbutton(bg, text="Start the tray app when I log in to Windows", variable=self.startup_var,
                        command=self.save_startup).grid(row=1, column=0, sticky="w")
        ttk.Label(bg, text=("Tray icon: on" if HAVE_TRAY else "Tray icon: off (run  pip install pystray pillow  to turn it on)")
                  ).grid(row=2, column=0, sticky="w")
        share = ttk.LabelFrame(tab, text="Share or start over", padding=8)
        share.pack(fill="x", pady=8)
        ttk.Button(share, text="Export my settings...", command=self.export_settings).pack(side="left")
        ttk.Button(share, text="Import settings...", command=self.import_settings).pack(side="left", padx=6)
        ttk.Button(share, text="Reset to Standard", command=self.reset_standard).pack(side="left")
        ttk.Button(share, text="Open my data folder", command=self.open_data_folder).pack(side="left", padx=6)
        ttk.Label(tab, text=f"Your settings and undo history live in: {self.backend.data_dir}").pack(anchor="w")

    def refresh_settings(self):
        try:
            name, custom = self.backend.current_preset()
            opts = self.backend.get_options()
        except ab.BackendError as exc:
            return self.show_error(exc)
        self.preset_label.set(f"Now using: {name}" + ("  (with your own changes)" if custom else ""))
        if self.presets and not self.preset_combo.get():
            self.preset_combo.set(self.presets[0]["name"])
        self.show_preset_text()
        self.opt_conflict.set(opts["on_conflict"])
        self.opt_age.set(str(opts["min_age_seconds"]))
        self.opt_recursive.set(bool(opts["recursive"]))
        self.opt_dedupe.set(bool(opts["dedupe_identical"]))
        app = self.backend.app_settings()
        self.auto_var.set(bool(app["auto_enabled"]))
        self.auto_minutes.set(str(app["auto_minutes"]))
        self.startup_var.set(self.backend.startup_enabled())

    def _chosen_preset(self):
        name = self.preset_combo.get()
        return next((p for p in self.presets if p["name"] == name), None)

    def show_preset_text(self):
        preset = self._chosen_preset()
        self.preset_text.set(preset["description"] if preset else "")

    def apply_preset(self):
        preset = self._chosen_preset()
        if not preset:
            return
        if messagebox.askyesno(TITLE, f"Switch to '{preset['name']}'?\nYour watched folders and ignore list are kept; "
                                      f"a backup of your current settings is saved."):
            self._settings_action(lambda: self.backend.apply_preset(preset["key"]), "Way of organizing changed.")

    def _settings_action(self, fn, ok_message):
        try:
            fn()
            self.status.set(ok_message)
        except ab.BackendError as exc:
            self.show_error(exc)
        self.refresh_settings()

    def save_options(self):
        try:
            age = int(self.opt_age.get())
        except ValueError:
            return messagebox.showwarning(TITLE, "The age must be a whole number of seconds.")
        self._settings_action(lambda: self.backend.set_options(on_conflict=self.opt_conflict.get(), min_age_seconds=age,
                                                               recursive=bool(self.opt_recursive.get()),
                                                               dedupe_identical=bool(self.opt_dedupe.get())), "Options saved.")

    def save_auto(self):
        try:
            minutes = max(5, int(self.auto_minutes.get()))
        except ValueError:
            minutes = 30
        self.backend.set_app_settings(auto_enabled=bool(self.auto_var.get()), auto_minutes=minutes)
        self._schedule_auto()
        self.status.set("Background tidying " + ("on." if self.auto_var.get() else "off."))

    def save_startup(self):
        try:
            self.backend.set_startup(bool(self.startup_var.get()))
            self.status.set("Saved.")
        except ab.BackendError as exc:
            self.startup_var.set(False)
            self.show_error(exc)

    def export_settings(self):
        path = filedialog.asksaveasfilename(defaultextension=".json", initialfile="my_organizer_settings.json")
        if path:
            self._settings_action(lambda: self.backend.export_settings(path), "Settings exported.")

    def import_settings(self):
        path = filedialog.askopenfilename(filetypes=[("Organizer settings", "*.json")])
        if path and messagebox.askyesno(TITLE, "Replace your rules with the ones in this file? (A backup is kept.)"):
            self._settings_action(lambda: self.backend.import_settings(path), "Settings imported.")

    def reset_standard(self):
        if messagebox.askyesno(TITLE, "Go back to the Standard way of organizing? (A backup is kept.)"):
            self._settings_action(self.backend.reset_to_standard, "Back to Standard.")

    def open_data_folder(self):
        try:
            if sys.platform.startswith("win"):
                os.startfile(str(self.backend.data_dir))            # noqa
            else:
                messagebox.showinfo(TITLE, str(self.backend.data_dir))
        except OSError as exc:
            messagebox.showwarning(TITLE, str(exc))

    # ---------------------------------------------------------------- first run
    def first_run_wizard(self):
        names = [p["name"] for p in self.backend.list_presets()]
        text = ("Welcome! Pick how you like your files organized. You can change this any time in Settings.\n\n"
                + "\n".join(f"{i + 1}. {p['name']}: {p['description']}" for i, p in enumerate(self.backend.list_presets()))
                + "\n\nType the number (1 = Standard).")
        answer = simpledialog.askstring(TITLE, text, initialvalue="1")
        try:
            chosen = self.backend.list_presets()[int(answer) - 1] if answer else None
        except (ValueError, IndexError):
            chosen = None
        if chosen and chosen["key"] != "standard":
            try:
                self.backend.apply_preset(chosen["key"])
            except ab.BackendError as exc:
                self.show_error(exc)
        downloads = Path.home() / "Downloads"
        if downloads.is_dir() and messagebox.askyesno(TITLE, f"Keep your Downloads folder tidy?\n{downloads}"):
            try:
                self.backend.add_watch(str(downloads))
            except ab.BackendError:
                pass
        self.backend.set_app_settings(first_run_done=True)
        self.refresh_settings()

    # ---------------------------------------------------------------- tray + background timer
    def _start_tray(self):
        if not HAVE_TRAY:
            return
        image = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)
        draw.rounded_rectangle((4, 14, 60, 54), radius=6, fill=(42, 111, 219, 255))
        draw.rounded_rectangle((4, 8, 28, 20), radius=4, fill=(42, 111, 219, 255))
        draw.rectangle((12, 28, 52, 32), fill=(255, 255, 255, 255))
        draw.rectangle((12, 38, 44, 42), fill=(255, 255, 255, 255))

        def post(fn):
            return lambda icon=None, item=None: self.q.put(fn)
        menu = pystray.Menu(
            pystray.MenuItem("Open Organizer", post(self.show_window), default=True),
            pystray.MenuItem("Organize my watched folders now", post(self.tray_organize)),
            pystray.MenuItem("Pause for 1 hour", post(lambda: self._rule_dash(lambda: self.backend.snooze("1h")))),
            pystray.MenuItem("Resume", post(lambda: self._rule_dash(self.backend.resume))),
            pystray.MenuItem("Quit", post(self.quit_app)))
        self.tray = pystray.Icon("Organizer", image, TITLE, menu)
        self.tray.run_detached()

    def show_window(self):
        self.root.deiconify()
        self.root.lift()

    def tray_organize(self):
        self.bg(lambda: self.backend.run_all(dry_run=False), self._tray_done, "Organizing watched folders...")

    def _tray_done(self, results, error):
        if error:
            return self.show_error(error)
        moved = sum(r["stats"].get("moved", 0) for _f, r in results)
        self.status.set(f"Watched folders: {moved} file(s) moved.")
        if self.tray:
            self.tray.notify(f"{moved} file(s) organized." if results else "No watched folders yet.", TITLE)

    def _schedule_auto(self):
        if self._auto_job is not None:
            self.root.after_cancel(self._auto_job)
            self._auto_job = None
        app = self.backend.app_settings()
        if app["auto_enabled"]:
            self._auto_job = self.root.after(max(5, int(app["auto_minutes"])) * 60 * 1000, self._auto_tick)

    def _auto_tick(self):
        self._auto_job = None
        self.bg(lambda: self.backend.run_all(dry_run=False, scheduled=True), self._tray_done, "Tidying watched folders...")
        self._schedule_auto()

    def on_close(self):
        if self.tray:
            self.root.withdraw()
            if not self.backend.app_settings().get("tray_hint_shown"):
                self.tray.notify("Organizer is still running here. Right-click the icon to quit.", TITLE)
                self.backend.set_app_settings(tray_hint_shown=True)
        else:
            self.quit_app()

    def quit_app(self):
        if self.tray:
            try:
                self.tray.stop()
            except Exception:
                pass
        self.root.destroy()

    def run(self):
        self.root.mainloop()
