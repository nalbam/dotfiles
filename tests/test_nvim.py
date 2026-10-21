#!/usr/bin/env python3
"""Offline regression tests for the Neovim configuration installer."""

import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parent.parent


class NeovimInstallerTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="dotfiles-nvim-")
        self.addCleanup(temporary.cleanup)
        self.home = Path(temporary.name)
        self.config = self.home / ".config/nvim"
        fixture_bin = self.home / "bin"
        fixture_bin.mkdir()
        date = fixture_bin / "date"
        date.write_text('#!/bin/sh\nprintf "20260101-000000\\n"\n')
        date.chmod(0o755)
        self.env = dict(os.environ, HOME=str(self.home),
                        PATH=str(fixture_bin) + os.pathsep + os.environ["PATH"])

    def install(self):
        result = subprocess.run(["/bin/bash", str(ROOT / "nvim/install.sh")],
                                env=self.env, capture_output=True, text=True, timeout=5)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        source = ROOT / "nvim/nvim"
        for file in source.rglob("*"):
            if file.is_file():
                self.assertEqual((self.config / file.relative_to(source)).read_bytes(), file.read_bytes())
        return result

    def test_first_install(self):
        self.install()
        self.assertEqual(list(self.config.parent.glob("nvim.bak-*")), [])

    def test_repeated_timestamp_preserves_each_configuration(self):
        for version in range(3):
            self.config.mkdir(parents=True, exist_ok=True)
            (self.config / "personal").write_text(str(version))
            result = self.install()
            suffix = "" if version == 0 else f"-{version}"
            backup = self.config.with_name("nvim.bak-20260101-000000" + suffix)
            self.assertEqual((backup / "personal").read_text(), str(version))
            self.assertIn(str(backup), result.stdout)
            self.assertFalse((backup / "nvim").exists())
        self.assertEqual(len(list(self.config.parent.glob("nvim.bak-*"))), 3)

    def test_dangling_symlink_is_backed_up(self):
        self.config.parent.mkdir(parents=True)
        self.config.symlink_to(self.home / "missing-config", target_is_directory=True)
        self.install()
        backup = self.config.with_name("nvim.bak-20260101-000000")
        self.assertTrue(backup.is_symlink())
        self.assertEqual(backup.readlink(), self.home / "missing-config")
        self.assertFalse(self.config.is_symlink())


if __name__ == "__main__":
    unittest.main()
