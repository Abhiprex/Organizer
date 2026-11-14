"""One shared setup: the desktop app, the command line, the folders menu, repair and the scheduled task
all use the same settings, the same pause switch and the same undo history - per user."""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC = HERE.parent / "src"
sys.path.insert(0, str(SRC))
import app_backend as ab  # noqa: E402

WORK = None


def setUpModule():
    global WORK
    WORK = Path(tempfile.mkdtemp(prefix="organizer-shared-"))


def tearDownModule():
    shutil.rmtree(WORK, ignore_errors=True)


def program_copy(name):
    """A private copy of the program folder (like an installed one)."""
    dest = WORK / name
    shutil.copytree(SRC, dest, ignore=shutil.ignore_patterns("__pycache__", "history"))
    return dest


def folder_with(name, files, age_days=1):
    folder = WORK / name
    shutil.rmtree(folder, ignore_errors=True)
    folder.mkdir(parents=True)
    for rel in files:
        (folder / rel).write_text(rel, encoding="utf-8")
        stamp = time.time() - age_days * 86400
        os.utime(folder / rel, (stamp, stamp))
    return folder


def cli(prog, home, *args, cwd=None, portable=False, **extra):
    env = {**os.environ, "HOME": str(WORK / "fakehome"), "USERPROFILE": str(WORK / "fakehome"),
           "APPDATA": str(WORK / "fakehome" / "AppData"), "XDG_DATA_HOME": str(WORK / "fakehome" / "share")}
    env.pop("ORGANIZER_HOME", None)
    env.pop("ORGANIZER_PORTABLE", None)
    if home:
        env["ORGANIZER_HOME"] = str(home)
    if portable:
        env["ORGANIZER_PORTABLE"] = "1"
    env.update(extra)
    done = subprocess.run([sys.executable, *args], cwd=cwd or prog, env=env, capture_output=True, timeout=120)
    return done.returncode, (done.stdout + done.stderr).decode("utf-8", "replace")


def organizer(prog, home, folder, *args, **kw):
    return cli(prog, home, "organizer.py", "-s", str(folder), "-y", "--min-age", "0", *args, **kw)


def names(folder):
    return sorted(str(p.relative_to(folder)).replace("\\", "/") for p in Path(folder).rglob("*") if p.is_file())


class SharedSetupTests(unittest.TestCase):
    def setUp(self):
        self.prog = program_copy(f"prog{time.time_ns()}")
        self.home = WORK / f"user{time.time_ns()}"
        self.app = ab.Backend(self.home)

    def test_app_run_is_visible_to_the_command_line_and_undoable_there(self):
        f = folder_with("a1", ["a.pdf", "b.jpg"])
        self.app.run(f, dry_run=False, include_new=True)
        rc, out = organizer(self.prog, self.home, f, "--history")
        self.assertIn(self.app.history(f)[0]["run"], out)
        organizer(self.prog, self.home, f, "--undo")
        self.assertEqual(names(f), ["a.pdf", "b.jpg"])
        self.assertEqual(self.app.history(f), [])

    def test_command_line_run_is_visible_to_the_app_and_undoable_there(self):
        f = folder_with("a2", ["a.pdf", "b.jpg"])
        organizer(self.prog, self.home, f)
        self.assertEqual(len(self.app.history(f)), 1)
        self.app.undo(f)
        self.assertEqual(names(f), ["a.pdf", "b.jpg"])

    def test_scheduled_task_follows_the_apps_watched_folders(self):
        f = folder_with("a3", ["a.pdf", "b.jpg"])
        self.app.add_watch(f)
        rc, out = cli(self.prog, self.home, "organizer.py", "-y", "--all", "--scheduled", "--min-age", "0")
        self.assertEqual(rc, 0, out)
        self.assertIn("Documents/PDF/a.pdf", names(f))
        self.assertEqual(len(self.app.history(f)), 1)                 # and the app can undo what the task did

    def test_scheduled_task_follows_the_apps_rules(self):
        f = folder_with("a4", ["invoice 1.pdf", "other.pdf"])
        self.app.add_rule({"name": "Bills", "extensions": ["pdf"], "patterns": ["invoice*"], "dest": "Money/Bills"})
        self.app.add_watch(f)
        cli(self.prog, self.home, "organizer.py", "-y", "--all", "--scheduled", "--min-age", "0")
        self.assertEqual(names(f), ["Documents/PDF/other.pdf", "Money/Bills/invoice 1.pdf"])

    def test_pause_set_in_the_app_stops_the_task_but_not_a_manual_run(self):
        f = folder_with("a5", ["a.pdf"])
        self.app.add_watch(f)
        self.app.snooze("1h")
        rc, out = cli(self.prog, self.home, "organizer.py", "-y", "--all", "--scheduled", "--min-age", "0")
        self.assertEqual(names(f), ["a.pdf"], out)
        organizer(self.prog, self.home, f)
        self.assertEqual(names(f), ["Documents/PDF/a.pdf"])

    def test_pause_and_resume_from_the_command_line_show_in_the_app(self):
        cli(self.prog, self.home, "organizer.py", "--snooze", "1h")
        self.assertIsNotNone(self.app.pause_status())
        cli(self.prog, self.home, "organizer.py", "--resume")
        self.assertIsNone(self.app.pause_status())

    def test_folders_menu_edits_the_same_settings_as_the_app(self):
        f = folder_with("a6", [])
        rc, out = cli(self.prog, self.home, "manage_folders.py", "watch-add", str(f))
        self.assertEqual(rc, 0, out)
        self.assertIn(str(f), self.app.get_watch())

    def test_doctor_reports_the_per_user_history_folder(self):
        rc, out = cli(self.prog, self.home, "organizer.py", "--doctor")
        self.assertIn(str(self.home), out)

    def test_repair_check_uses_the_per_user_folder_and_finds_no_problem(self):
        rc, out = cli(self.prog, self.home, "repair.py", "--check")
        self.assertIn("0 problem(s)", out)

    def test_two_users_never_see_each_others_history(self):
        f = folder_with("a7", ["a.pdf"])
        organizer(self.prog, self.home, f)
        other = WORK / f"other{time.time_ns()}"
        rc, out = organizer(self.prog, other, f, "--history")
        self.assertNotIn("1 item", out)
        self.assertEqual(ab.Backend(other).history(f), [])


class MigrationTests(unittest.TestCase):
    def test_history_made_next_to_the_program_is_copied_to_the_user_folder_once(self):
        prog = program_copy(f"old{time.time_ns()}")
        f = folder_with("m1", ["a.pdf", "b.jpg"])
        organizer(prog, None, f, portable=True)                        # the old layout: history inside the program folder
        self.assertTrue(list((prog / "history").glob("*.jsonl")))
        home = WORK / f"newuser{time.time_ns()}"
        rc, out = organizer(prog, home, f, "--history")               # now per-user: the old run is still there
        self.assertEqual(len(ab.Backend(home).history(f)), 1)
        self.assertTrue((home / "history" / ".migrated").exists())
        organizer(prog, home, f, "--undo")
        self.assertEqual(names(f), ["a.pdf", "b.jpg"])

    def test_portable_txt_keeps_everything_next_to_the_program(self):
        prog = program_copy(f"usb{time.time_ns()}")
        (prog / "portable.txt").write_text("keep my files here")
        f = folder_with("m2", ["a.pdf"])
        rc, out = organizer(prog, None, f)
        self.assertEqual(rc, 0, out)
        self.assertTrue(list((prog / "history").glob("*.jsonl")))
        self.assertFalse((WORK / "fakehome" / "share" / "organizer").exists())
        self.assertFalse((WORK / "fakehome" / "AppData" / "Organizer").exists())

    def test_first_command_line_run_creates_the_users_own_settings_copy(self):
        prog = program_copy(f"first{time.time_ns()}")
        home = WORK / f"fresh{time.time_ns()}"
        cli(prog, home, "organizer.py", "--doctor")
        self.assertTrue((home / "organizer_config.json").exists())

    def test_an_existing_watch_setup_is_kept_when_the_app_starts_for_the_first_time(self):
        prog = program_copy(f"inst{time.time_ns()}")
        f = folder_with("m3", ["a.pdf"])
        cfg = json.loads((prog / "organizer_config.json").read_text(encoding="utf-8-sig"))
        cfg["watch"] = [str(f)]
        (prog / "organizer_config.json").write_text(json.dumps(cfg), encoding="utf-8")
        home = WORK / f"appuser{time.time_ns()}"
        code = "import app_backend as ab; b = ab.Backend(); print(b.first_run, b.get_watch())"
        rc, out = cli(prog, home, "-c", code)
        self.assertIn("False", out)
        self.assertIn(str(f), out)

    def test_a_fresh_user_without_a_setup_starts_with_the_first_run_choice(self):
        prog = program_copy(f"fresh2{time.time_ns()}")
        home = WORK / f"brandnew{time.time_ns()}"
        code = "import app_backend as ab; b = ab.Backend(); print('FIRST', b.first_run, b.get_watch())"
        rc, out = cli(prog, home, "-c", code)
        self.assertIn("FIRST True []", out)


if __name__ == "__main__":
    unittest.main()
