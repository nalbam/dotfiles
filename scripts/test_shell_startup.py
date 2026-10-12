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
        self.brew_prefixes = {
            "/opt/homebrew": self.home / "brew-arm",
            "/home/linuxbrew/.linuxbrew": self.home / "brew-linux",
            "/usr/local": self.home / "brew-intel",
        }
        self.env = dict(os.environ, HOME=str(self.home),
                        PATH=str(self.bin) + ":/usr/bin:/bin", BASH_ENV="", ENV="",
                        ZDOTDIR=str(self.home), TERM_PROGRAM="", PROMPT="")
        for key in ("NVM_DIR", "NVM_BIN", "NVM_INC", "BREWPATH"):
            self.env.pop(key, None)
        self.env = {key: value for key, value in self.env.items() if not key.startswith("BASH_FUNC_")}

    def startup(self, shell, config, body=""):
        # Map installed-system prefixes into the fixture so no real plugin is sourced.
        source = (ROOT / config).read_text()
        for prefix, replacement in self.brew_prefixes.items():
            source = source.replace(prefix, str(replacement))
        fixture = self.home / config
        fixture.write_text(source)
        shared = ROOT / "shell/nvm.sh"
        if shared.is_file():
            source = shared.read_text()
            for prefix, replacement in self.brew_prefixes.items():
                source = source.replace(prefix, str(replacement))
            target = self.home / ".config/dotfiles/nvm.sh"
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(source)
        args = ["--noprofile", "--norc"] if shell.endswith("bash") else ["-f"]
        return subprocess.run([shell, *args, "-c",
                               'locale() { printf "UTF-8\\n"; }; . "$1"\n' + body,
                               "startup-test", str(fixture)], env=self.env,
                              capture_output=True, text=True, timeout=5)

    def nvm_fixture(self, version="24.21.0", installation="brew", custom_dir=False,
                    platform="/opt/homebrew"):
        nvm_dir = self.home / ("custom nvm" if custom_dir else ".nvm")
        node_bin = nvm_dir / "versions/node" / f"v{version}" / "bin"
        node_bin.mkdir(parents=True)
        (node_bin / "node").write_text(f'#!/bin/sh\nprintf "v{version}\\n"\n')
        (node_bin / "node").chmod(0o755)
        system_bin = self.brew_prefixes[platform] / "bin"
        system_bin.mkdir(parents=True)
        (system_bin / "node").write_text('#!/bin/sh\nprintf "v26.11.1\\n"\n')
        (system_bin / "node").chmod(0o755)
        loader = (self.brew_prefixes[platform] / "opt/nvm/nvm.sh") if installation == "brew" else nvm_dir / "nvm.sh"
        loader.parent.mkdir(parents=True, exist_ok=True)
        loader.write_text('nvm() { :; }\nexport NVM_BIN=' + shlex.quote(str(node_bin)) + '\n')
        self.env["PATH"] = str(system_bin) + ":" + str(node_bin) + ":/usr/bin:/bin"
        if custom_dir:
            self.env["NVM_DIR"] = str(nvm_dir)
        return node_bin

    def assert_nvm_priority(self, platform):
        node_bin = self.nvm_fixture(platform=platform)
        for shell, config in (("/bin/bash", "bashrc"), ("/bin/zsh", "zshrc")):
            if not Path(shell).is_file():
                continue
            with self.subTest(shell=shell):
                result = self.startup(shell, config, 'node --version; . "$1"; node --version; command -v node')
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(result.stderr, "")
                self.assertEqual(result.stdout.splitlines(), ["v24.21.0", "v24.21.0", str(node_bin / "node")])

    def test_macos_arm_nvm_wins_after_repeated_startup(self):
        self.assert_nvm_priority("/opt/homebrew")

    def test_macos_intel_nvm_wins_after_repeated_startup(self):
        self.assert_nvm_priority("/usr/local")

    def test_linux_nvm_wins_after_repeated_startup(self):
        self.assert_nvm_priority("/home/linuxbrew/.linuxbrew")

    def test_user_nvm_installation_and_explicitly_selected_version_are_preserved(self):
        node_bin = self.nvm_fixture(version="22.20.0", installation="user", custom_dir=True)
        for shell, config in (("/bin/bash", "bashrc"), ("/bin/zsh", "zshrc")):
            if not Path(shell).is_file():
                continue
            with self.subTest(shell=shell):
                result = self.startup(shell, config, 'node --version; command -v node; printf "%s\\n" "$NVM_DIR"')
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(result.stderr, "")
                self.assertEqual(result.stdout.splitlines(), ["v22.20.0", str(node_bin / "node"), str(self.home / "custom nvm")])

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
