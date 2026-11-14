"""The launcher (organizer_app.py): self-test, crash report, only-one-copy check. No window is ever opened."""
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SRC = Path(__file__).resolve().parent.parent / "src"


class LauncherTests(unittest.TestCase):
    def setUp(self):
        self.work = Path(tempfile.mkdtemp(prefix="organizer-launch-"))
        self.home = self.work / "home"
        self.addCleanup(shutil.rmtree, self.work, True)

    def launch(self, *args, **extra_env):
        env = {**os.environ, "ORGANIZER_HOME": str(self.home), "ORGANIZER_APP_NO_DIALOG": "1", **extra_env}
        done = subprocess.run([sys.executable, str(SRC / "organizer_app.py"), *args], cwd=self.work, env=env,
                              capture_output=True, timeout=60)
        return done.returncode, (done.stdout + done.stderr).decode("utf-8", "replace")

    def test_selftest_prints_a_plain_report_and_saves_it(self):
        rc, out = self.launch("--selftest")
        self.assertIn("self-test", out)
        self.assertIn("Python", out)
        self.assertIn("your data folder is writable", out)
        self.assertIn("ways of organizing found", out)
        self.assertTrue((self.home / "selftest.txt").exists())
        self.assertIn(rc, (0, 1))                                  # 1 only if Tkinter / a screen is missing here

    def test_selftest_twice_changes_nothing(self):
        self.launch("--selftest")
        before = (self.home / "organizer_config.json").read_bytes()
        self.launch("--selftest")
        self.assertEqual((self.home / "organizer_config.json").read_bytes(), before)

    def test_a_crash_leaves_a_report_file_instead_of_vanishing(self):
        rc, out = self.launch(ORGANIZER_APP_TEST_CRASH="1")
        self.assertEqual(rc, 1)
        report = self.home / "startup_error.txt"
        self.assertTrue(report.exists())
        self.assertIn("test crash", report.read_text(encoding="utf-8"))
        self.assertIn("startup_error.txt", out)

    def test_second_copy_is_refused_while_the_first_is_alive(self):
        self.home.mkdir(parents=True)
        (self.home / "app.lock").write_text(str(os.getpid()))      # this test process stands in for the running app
        rc, out = self.launch(ORGANIZER_APP_NO_GUI="1")
        self.assertEqual(rc, 0)
        self.assertIn("already running", out)
        self.assertFalse(any(line.strip() == "ready" for line in out.splitlines()))

    def test_a_leftover_lock_from_a_crash_does_not_block_start(self):
        dead = subprocess.Popen([sys.executable, "-c", "pass"])
        dead.wait()
        self.home.mkdir(parents=True)
        (self.home / "app.lock").write_text(str(dead.pid))
        rc, out = self.launch(ORGANIZER_APP_NO_GUI="1")
        self.assertEqual(rc, 0)
        self.assertTrue(any(line.strip() == "ready" for line in out.splitlines()))

    def test_lock_is_released_when_the_app_ends(self):
        self.launch(ORGANIZER_APP_NO_GUI="1")
        self.assertFalse((self.home / "app.lock").exists())


if __name__ == "__main__":
    unittest.main()
