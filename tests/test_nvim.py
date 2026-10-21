#!/usr/bin/env python3
"""Offline regression tests for the Neovim configuration module (modules/nvim.sh)."""

import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parent.parent


class NeovimModuleTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="dotfiles-nvim-")
        self.addCleanup(temporary.cleanup)
        self.home = Path(temporary.name) / "home"
        self.config = self.home / ".config/nvim"
        # A fixture checkout lets a test change the repository configuration.
        self.repo = Path(temporary.name) / "repo"
        self.source = self.repo / "config/nvim/nvim"
        shutil.copytree(ROOT / "config/nvim/nvim", self.source)
        fixture_bin = Path(temporary.name) / "bin"
        fixture_bin.mkdir()
        date = fixture_bin / "date"
        date.write_text('#!/bin/sh\nprintf "20260101-000000\\n"\n')
        date.chmod(0o755)
        self.home.mkdir()
        self.env = {key: value for key, value in os.environ.items()
                    if not key.startswith(("XDG_", "DOT_", "BASH_FUNC_"))}
        self.env.update(HOME=str(self.home), DOT_HOME=str(self.repo), DOT_COLOR="false",
                        PATH=str(fixture_bin) + os.pathsep + os.environ["PATH"])

    def install(self, nvim_installed=True):
        # Decide whether nvim exists independently of the machine running the tests.
        presence = '[ "$1" = nvim ] ||' if nvim_installed else '[ "$1" != nvim ] &&'
        script = (f'. "{ROOT}/lib/core.sh"\n'
                  f'dot_has() {{ {presence} command -v "$1" >/dev/null 2>&1; }}\n'
                  f'. "{ROOT}/modules/nvim.sh"\nnvim::up\n')
        result = subprocess.run(["/bin/bash", "-c", script],
                                env=self.env, capture_output=True, text=True, timeout=5)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return result

    def assert_matches_source(self):
        for file in self.source.rglob("*"):
            if file.is_file():
                self.assertEqual((self.config / file.relative_to(self.source)).read_bytes(), file.read_bytes())

    def backups(self):
        return sorted(self.config.parent.glob("nvim.bak-*"))

    def test_first_install(self):
        result = self.install()
        self.assert_matches_source()
        self.assertEqual(self.backups(), [])
        self.assertIn("Installed ~/.config/nvim", result.stdout)
        self.assertTrue((self.home / ".local/state/dotfiles/applied/nvim").is_file())

    def test_local_changes_survive_when_the_repository_is_unchanged(self):
        self.install()
        # Neovim writes lazy-lock.json and plugin state into the directory.
        (self.config / "lazy-lock.json").write_text("{}\n")
        (self.config / "init.lua").write_text("-- local edit\n")
        result = self.install()
        self.assertIn("Configuration is current", result.stdout)
        self.assertEqual((self.config / "init.lua").read_text(), "-- local edit\n")
        self.assertTrue((self.config / "lazy-lock.json").exists())
        self.assertEqual(self.backups(), [])

    def test_repository_change_replaces_with_backups(self):
        self.install()
        for version in range(1, 4):
            (self.config / "personal").write_text(str(version))
            (self.source / "added.lua").write_text(f"-- version {version}\n")
            result = self.install()
            self.assert_matches_source()
            backup = self.config.with_name("nvim.bak-20260101-000000" + ".1" * (version - 1))
            self.assertEqual((backup / "personal").read_text(), str(version))
            self.assertIn(str(backup), result.stdout)
            self.assertFalse((backup / "nvim").exists())
            self.assertFalse((self.config / "personal").exists())
        self.assertEqual(len(self.backups()), 3)

    def test_dangling_symlink_is_moved_aside(self):
        self.config.parent.mkdir(parents=True)
        self.config.symlink_to(self.home / "missing-config", target_is_directory=True)
        self.install()
        backup = self.config.with_name("nvim.bak-20260101-000000")
        self.assertTrue(backup.is_symlink())
        self.assertEqual(backup.readlink(), self.home / "missing-config")
        self.assertFalse(self.config.is_symlink())
        self.assert_matches_source()

    def test_missing_nvim_binary_warns(self):
        result = self.install(nvim_installed=False)
        self.assertIn("nvim is not installed", result.stdout)
        result = self.install(nvim_installed=True)
        self.assertNotIn("nvim is not installed", result.stdout)


if __name__ == "__main__":
    unittest.main()
