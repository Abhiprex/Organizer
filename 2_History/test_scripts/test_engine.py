"""Command-line engine tests: they copy src/ to a temp folder and run organizer.py on throw-away folders."""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

SRC = Path(__file__).resolve().parent.parent / "src"
WORK = None
PROG = None


def setUpModule():
    global WORK, PROG
    WORK = Path(tempfile.mkdtemp(prefix="organizer-test-"))
    PROG = WORK / "prog"
    shutil.copytree(SRC, PROG, ignore=shutil.ignore_patterns("__pycache__", "history"))


def tearDownModule():
    shutil.rmtree(WORK, ignore_errors=True)


def make(name, files, age_days=1):
    folder = WORK / name
    shutil.rmtree(folder, ignore_errors=True)
    folder.mkdir(parents=True)
    for rel, text in files.items():
        target = folder / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")
        stamp = time.time() - age_days * 86400
        os.utime(target, (stamp, stamp))
    return folder


def run(folder, *args, cfg=None, timeout=60):
    cmd = [sys.executable, "organizer.py", "-s", str(folder), "-y", "--min-age", "0", *args]
    if cfg:
        cmd += ["-c", str(cfg)]
    done = subprocess.run(cmd, cwd=PROG, capture_output=True, timeout=timeout)
    return done.returncode, (done.stdout + done.stderr).decode("utf-8", "replace")


def files_in(folder):
    return sorted(str(p.relative_to(folder)).replace("\\", "/") for p in Path(folder).rglob("*") if p.is_file())


def config_with(rule=None):
    cfg = json.loads((PROG / "organizer_config.json").read_text(encoding="utf-8-sig"))
    if rule:
        cfg["rules"].insert(0, rule)
    path = WORK / f"cfg{time.time_ns()}.json"
    path.write_text(json.dumps(cfg), encoding="utf-8")
    return path


class EngineTests(unittest.TestCase):
    def test_version(self):
        rc, out = run(WORK, "--version")
        self.assertEqual(rc, 0)
        self.assertIn("Organizer", out)

    def test_sorts_by_type(self):
        f = make("sort", {"a.pdf": "1", "b.jpg": "2", "c.mp3": "3", "d.zip": "4", "e.py": "5", "Makefile": "6"})
        rc, out = run(f)
        self.assertEqual(rc, 0, out)
        got = files_in(f)
        for expected in ("Documents/PDF/a.pdf", "Images/JPG/b.jpg", "Audio/MP3/c.mp3", "Archives/d.zip", "Code/Build/Makefile"):
            self.assertIn(expected, got)

    def test_dry_run_moves_nothing(self):
        f = make("dry", {"a.pdf": "1"})
        run(f, "-n")
        self.assertEqual(files_in(f), ["a.pdf"])

    def test_second_run_is_idle(self):
        f = make("idle", {"a.pdf": "1", "b.jpg": "2"})
        run(f)
        rc, out = run(f)
        self.assertIn("0 moved", out)

    def test_undo_restores_everything(self):
        f = make("undo", {"a.pdf": "1", "b.jpg": "2", "c.mp3": "3"})
        run(f)
        run(f, "--undo")
        self.assertEqual(files_in(f), ["a.pdf", "b.jpg", "c.mp3"])
        rc, out = run(f, "--undo")
        self.assertIn("nothing to undo", out)

    def test_name_clash_keeps_both(self):
        f = make("clash", {"a.pdf": "new"})
        (f / "Documents" / "PDF").mkdir(parents=True)
        (f / "Documents" / "PDF" / "a.pdf").write_text("old")
        run(f)
        self.assertEqual((f / "Documents/PDF/a.pdf").read_text(), "old")
        self.assertEqual((f / "Documents/PDF/a (1).pdf").read_text(), "new")

    def test_identical_copy_is_set_aside(self):
        f = make("dupe", {"a.pdf": "same"})
        (f / "Documents" / "PDF").mkdir(parents=True)
        (f / "Documents" / "PDF" / "x.pdf").write_text("same")
        run(f)
        self.assertTrue(any(p.startswith("_Duplicates") for p in files_in(f)))

    def test_hidden_partial_and_office_temp_files_are_left_alone(self):
        f = make("skip", {".hidden.pdf": "1", "dl.pdf.part": "2", "~$doc.docx": "3", "ok.pdf": "4"})
        run(f)
        got = files_in(f)
        for stay in (".hidden.pdf", "dl.pdf.part", "~$doc.docx"):
            self.assertIn(stay, got)
        self.assertIn("Documents/PDF/ok.pdf", got)

    def test_unknown_type_goes_to_other(self):
        f = make("unknown", {"a.qqq": "1"})
        run(f)
        self.assertIn("Other/QQQ/a.qqq", files_in(f))

    def test_future_dated_file_is_organized(self):
        f = make("future", {"a.pdf": "1"})
        os.utime(f / "a.pdf", (4102444800, 4102444800))        # the year 2100
        run(f)
        self.assertIn("Documents/PDF/a.pdf", files_in(f))

    def test_rule_extension_without_dot_works(self):
        f = make("dotless", {"a.pdf": "1"})
        cfg = config_with({"name": "mine", "extensions": ["pdf"], "dest": "MyPDFs", "custom": True})
        run(f, cfg=cfg)
        self.assertIn("MyPDFs/a.pdf", files_in(f))

    def test_rule_cannot_send_files_outside_the_folder(self):
        base = make("outside", {})
        inner = base / "in"
        inner.mkdir()
        (inner / "a.pdf").write_text("1")
        cfg = config_with({"name": "esc", "extensions": [".pdf"], "dest": "../escaped", "custom": True})
        run(inner, cfg=cfg)
        self.assertFalse((base / "escaped").exists())

    def test_slow_regex_rule_cannot_freeze_a_run(self):
        f = make("regex", {"a" * 40 + "!.txt": "1", "ok.pdf": "2"})
        cfg = config_with({"name": "bomb", "regex": "^(a+)+$", "dest": "Bomb", "custom": True})
        rc, out = run(f, cfg=cfg, timeout=30)
        self.assertEqual(rc, 0, out)
        self.assertIn("Documents/PDF/ok.pdf", files_in(f))

    def test_unicode_and_odd_names(self):
        names = ["日本語.pdf", "émoji😀.jpg", "a b  c.pdf", "50%.pdf", "[x](y).pdf"]
        f = make("names", {n: "1" for n in names})
        rc, out = run(f)
        self.assertEqual(rc, 0, out)
        self.assertIn(" 0 errors", out)
        self.assertEqual(len(files_in(f)), len(names))

    @unittest.skipIf(os.name == "nt", "needs 255-character names, which hit the Windows path limit")
    def test_long_name_clash_is_shortened(self):
        name = "x" * 251 + ".pdf"
        f = make("long", {name: "new"})
        (f / "Documents" / "PDF").mkdir(parents=True)
        (f / "Documents" / "PDF" / name).write_text("old")
        rc, out = run(f)
        self.assertIn(" 0 errors", out)
        self.assertEqual(len(files_in(f)), 2)

    def test_many_files_and_idempotent(self):
        f = make("many", {f"f{i}.{['pdf', 'jpg', 'txt', 'zip'][i % 4]}": str(i % 50) for i in range(1500)})
        rc, out = run(f, timeout=120)
        self.assertEqual(rc, 0, out)
        self.assertEqual(len(files_in(f)), 1500)
        rc, out = run(f)
        self.assertIn("0 moved", out)

    def test_undo_after_chaotic_names_restores_exact_names(self):
        names = ["Ünïcode ñame.PDF", "weird name (1).Jpg", "no_extension", "UPPER.MP3", "multi.part.name.docx", "日本.txt"]
        f = make("chaos", {n: str(i) for i, n in enumerate(names)})
        run(f)
        run(f, "--undo")
        self.assertEqual(files_in(f), sorted(names))


if __name__ == "__main__":
    unittest.main()
