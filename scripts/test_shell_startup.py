#!/usr/bin/env python3
"""Offline checks for shell startup PATH construction."""

import os
from pathlib import Path
import shlex
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parent.parent


class ShellStartupTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="dotfiles-startup-")
        self.addCleanup(temporary.cleanup)
        self.home = Path(temporary.name) / "machine home"
        self.home.mkdir()
        self.bin = self.home / "bin"
        self.bin.mkdir()
        self.env = dict(os.environ, HOME=str(self.home),
                        PATH=str(self.bin) + ":/usr/bin:/bin", BASH_ENV="", ENV="",
                        ZDOTDIR=str(self.home), TERM_PROGRAM="", PROMPT="")

    def startup(self, shell, config, body=""):
        # Map installed-system prefixes into the fixture so no real plugin is sourced.
        source = (ROOT / config).read_text()
        for prefix in ("/opt/homebrew", "/home/linuxbrew/.linuxbrew", "/usr/local"):
            source = source.replace(prefix, str(self.home / "brew"))
        fixture = self.home / config
        fixture.write_text(source)
        args = ["--noprofile", "--norc"] if shell.endswith("bash") else ["-f"]
        return subprocess.run([shell, *args, "-c",
                               'locale() { printf "UTF-8\\n"; }; . "$1"\n' + body,
                               "startup-test", str(fixture)], env=self.env,
                              capture_output=True, text=True, timeout=5)

    def test_path_prepend_does_not_search_current_directory(self):
        with tempfile.TemporaryDirectory(prefix="dotfiles-shell-") as temporary:
            home = Path(temporary)
            (home / "bin").mkdir()
            (home / ".local/bin").mkdir(parents=True)
            for config in ("bashrc", "profile"):
                for initial_path in ("/usr/bin:/bin", ""):
                    with self.subTest(config=config, initial_path=initial_path):
                        env = dict(os.environ, HOME=str(home), PATH=initial_path,
                                   TERM_PROGRAM="", BASH_ENV="", ENV="")
                        result = subprocess.run(
                            ["/bin/bash", "--noprofile", "--norc", "-c",
                             'locale() { printf "UTF-8\\n"; }; . "$1"; printf "%s" "$PATH"',
                             "startup-test", str(ROOT / config)],
                            env=env, capture_output=True, text=True, timeout=5,
                        )
                        self.assertEqual(result.returncode, 0, result.stderr)
                        entries = result.stdout.split(os.pathsep)
                        self.assertNotIn("", entries)
                        self.assertIn(str(home / ".local/bin"), entries)
                        if initial_path:
                            self.assertEqual(entries[-2:], ["/usr/bin", "/bin"])

    def test_missing_optional_tools_do_not_break_startup(self):
        (self.home / ".pyenv").mkdir()
        (self.home / ".nvm").mkdir()
        for shell, config in (("/bin/bash", "bashrc"), ("/bin/zsh", "zshrc")):
            if not Path(shell).is_file():
                continue
            for terminal in ("vscode", "kiro"):
                with self.subTest(shell=shell, terminal=terminal):
                    self.env["TERM_PROGRAM"] = terminal
                    result = self.startup(shell, config)
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertEqual(result.stderr, "")

    def test_editor_integration_requires_successful_lookup_and_readable_file(self):
        integration = self.home / "editor integration.sh"
        integration.write_text('printf "editor loaded\\n"\n')
        for shell, config in (("/bin/bash", "bashrc"), ("/bin/zsh", "zshrc")):
            if not Path(shell).is_file():
                continue
            for terminal, cli in (("vscode", "code"), ("kiro", "kiro")):
                self.env["TERM_PROGRAM"] = terminal
                for status, path, expected in ((0, integration, "editor loaded\n"),
                                               (1, integration, ""),
                                               (0, self.home / "missing.sh", "")):
                    with self.subTest(shell=shell, terminal=terminal, status=status, path=path):
                        executable = self.bin / cli
                        executable.write_text("#!/bin/sh\nprintf '%s\\n' " + shlex.quote(str(path))
                                              + f"\nexit {status}\n")
                        executable.chmod(0o755)
                        result = self.startup(shell, config)
                        self.assertEqual(result.returncode, 0, result.stderr)
                        self.assertEqual(result.stderr, "")
                        self.assertEqual(result.stdout, expected)

    @unittest.skipUnless(Path("/bin/zsh").is_file(), "Zsh is not installed")
    def test_available_zsh_plugins_and_pyenv_are_loaded(self):
        plugin = self.home / ".oh-my-zsh/oh-my-zsh.sh"
        plugin.parent.mkdir()
        plugin.write_text('kube_ps1() { printf "kube"; }\n')
        (self.home / ".pyenv").mkdir()
        pyenv = self.bin / "pyenv"
        pyenv.write_text('#!/bin/sh\nprintf "export PYENV_INIT_DONE=yes\\n"\n')
        pyenv.chmod(0o755)
        result = self.startup("/bin/zsh", "zshrc", 'printf "%s\\n" "$PYENV_INIT_DONE" "$PROMPT" "${plugins[*]}"')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, "")
        self.assertEqual(result.stdout.splitlines(), ["yes", "$(kube_ps1)", "git kube-ps1"])


if __name__ == "__main__":
    unittest.main()
