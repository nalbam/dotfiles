#!/usr/bin/env python3
"""Offline regression tests for the Bash installer's file and package operations."""

import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parent.parent


class InstallerTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="dotfiles-installer-")
        self.addCleanup(temporary.cleanup)
        self.home = Path(temporary.name) / "home"
        self.repo = self.home / ".dotfiles"
        self.repo.mkdir(parents=True)
        self.source = (ROOT / "run.sh").read_text()
        self.declarations = self.source.split("# 실행 영역", 1)[0] + "\n}\nTPUT=\n"
        self.env = dict(os.environ, HOME=str(self.home), TERM="dumb", BASH_ENV="")

    def run_shell(self, body):
        return subprocess.run(["/bin/bash", "-c", self.declarations + body],
                              env=self.env, capture_output=True, text=True, timeout=5)

    def block(self, start, end):
        return self.source[self.source.index(start):self.source.index(end)]

    def test_every_git_identity_include_is_deployed_and_effective(self):
        for source in ROOT.glob("gitconfig*"):
            shutil.copy(source, self.repo / source.name)
        result = self.run_shell(self.block("# Git 설정 파일 다운로드", "# Step 5:"))
        self.assertEqual(result.returncode, 0, result.stderr)
        for account, profile in [("nalbam", "nalbam"), ("opspresso", "nalbam"),
                                 ("yujh404", "yujh404"), ("nalbam-me", "nalbam-me"),
                                 ("nalbam-bot", "nalbam-bot")]:
            with self.subTest(account=account):
                target = self.home / (".gitconfig-" + profile)
                self.assertTrue(target.is_file(), f"Missing identity profile: {profile}")
                workspace = self.home / "workspace/github.com" / account / "example"
                subprocess.run(["git", "init", "-q", str(workspace)], env=self.env, check=True)
                for key in ("user.name", "user.email"):
                    actual = subprocess.check_output(["git", "-C", str(workspace), "config", "--get", key], env=self.env)
                    expected = subprocess.check_output(["git", "config", "--file", str(ROOT / ("gitconfig-" + profile)), "--get", key], env=self.env)
                    self.assertTrue(actual == expected, f"Incorrect {key} for {profile}")


if __name__ == "__main__":
    unittest.main()
