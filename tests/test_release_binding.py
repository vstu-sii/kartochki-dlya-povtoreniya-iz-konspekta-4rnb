"""Release certification must identify the actual clean checkout."""
import importlib.util
import subprocess
import tempfile
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location("release_runner", Path(__file__).parent / "evals/run_release_evals.py")
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)

class ReleaseBindingTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.git("init")
        self.git("config", "user.email", "test@example.invalid")
        self.git("config", "user.name", "Release Test")
        (self.root / "source.txt").write_text("one")
        self.git("add", ".")
        self.git("commit", "-m", "initial")
        self.git("tag", "-a", "v-test", "-m", "release")

    def git(self, *args):
        return subprocess.check_output(["git", *args], cwd=self.root, stderr=subprocess.PIPE, text=True).strip()

    def test_clean_annotated_tag_is_accepted(self):
        self.assertEqual(runner.validate_release(self.root, "v-test"), (self.git("rev-parse", "HEAD"), False))

    def test_missing_tag_and_branch_are_rejected(self):
        self.git("branch", "only-branch")
        for ref in ("missing", "only-branch"):
            with self.subTest(ref=ref), self.assertRaises(ValueError):
                runner.validate_release(self.root, ref)

    def test_tag_at_another_commit_is_rejected(self):
        self.git("commit", "--allow-empty", "-m", "next")
        with self.assertRaises(ValueError):
            runner.validate_release(self.root, "v-test")

    def test_dirty_tracked_and_untracked_files_are_rejected(self):
        (self.root / "source.txt").write_text("two")
        with self.assertRaises(ValueError):
            runner.validate_release(self.root, "v-test")
        self.git("restore", "source.txt")
        (self.root / "extra.py").write_text("pass")
        with self.assertRaises(ValueError):
            runner.validate_release(self.root, "v-test")

    def test_worktree_is_always_candidate(self):
        (self.root / "source.txt").write_text("dirty")
        self.assertTrue(runner.validate_release(self.root, "WORKTREE")[1])

if __name__ == "__main__":
    unittest.main()
