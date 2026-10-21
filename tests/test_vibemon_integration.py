#!/usr/bin/env python3
"""Run both real installers offline against temporary homes.

DOTFILES_VIBEMON_INSTALLER=/path/to/vibemon-app/public/install/install.py \
    python3 scripts/test_vibemon_integration.py
"""

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parent.parent
INSTALLER = os.environ.get("DOTFILES_VIBEMON_INSTALLER")


@unittest.skipUnless(INSTALLER, "Set DOTFILES_VIBEMON_INSTALLER for the cross-repository check")
class InstallerCoexistenceTests(unittest.TestCase):
    def test_install_orders_reinstall_and_uninstall(self):
        for order in (("vibemon", "dotfiles"), ("dotfiles", "vibemon")):
            with self.subTest(order=order), tempfile.TemporaryDirectory() as directory:
                home = Path(directory) / "machine home"
                repo = home / ".dotfiles"
                repo.mkdir(parents=True)
                for name in ("claude", "codex", "kiro", "scripts"):
                    shutil.copytree(ROOT / name, repo / name, ignore=shutil.ignore_patterns("__pycache__"))
                shutil.copy(ROOT / "run.sh", repo / "run.sh")
                env = {"HOME": str(home), "PATH": os.environ["PATH"], "TERM": "dumb",
                       "PYENV_VERSION": "", "PYTHONIOENCODING": "utf-8"}
                foreign = {"matcher": "startup", "hooks": [{"type": "command", "command": "romty hook test"}]}
                for tool, filename in (("claude", "settings.json"), ("codex", "hooks.json")):
                    path = home / f".{tool}" / filename
                    path.parent.mkdir(parents=True)
                    path.write_text(json.dumps({"hooks": {"SessionStart": [foreign]}, "custom": False}))
                kiro_agent = home / ".kiro/agents/default.json"
                kiro_agent.parent.mkdir(parents=True)
                kiro_settings = {"hooks": [{"name": "user-hook", "trigger": "SessionStart",
                                           "action": {"type": "command", "command": "romty hook test"}}]}
                kiro_agent.write_text(json.dumps(kiro_settings))
                config = home / ".codex/config.toml"

                def run(kind, uninstall=False):
                    if kind == "dotfiles":
                        command = ["/bin/bash", str(repo / "run.sh"), "--vibe"]
                    else:
                        command = [sys.executable, str(Path(INSTALLER).resolve()),
                                   "--claude", "--codex", "--kiro", "--yes"]
                        if uninstall:
                            command.append("--uninstall")
                    result = subprocess.run(command, env=env, input="", capture_output=True,
                                            text=True, timeout=30)
                    self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

                def verify(installed=True):
                    for tool, filename in (("claude", "settings.json"), ("codex", "hooks.json")):
                        settings = json.loads((home / f".{tool}" / filename).read_text())
                        self.assertFalse(settings["custom"])
                        self.assertIn(foreign, settings["hooks"]["SessionStart"])
                        for event in ("SessionStart", "SessionEnd"):
                            commands = [hook["command"] for entry in settings["hooks"].get(event, [])
                                        for hook in entry["hooks"]]
                            self.assertEqual(sum("vibemon.py" in c for c in commands), int(installed))
                            self.assertFalse(any("memory-sync.sh" in c for c in commands))
                    self.assertEqual((home / ".kiro/hooks/vibemon.json").exists(), installed)
                    self.assertEqual(json.loads(kiro_agent.read_text()), kiro_settings)
                    self.assertFalse((home / ".claude/hooks/memory-sync.sh").exists())

                for kind in order:
                    run(kind)
                verify()
                original_config = config.read_bytes()
                for kind in order:
                    run(kind)
                verify()
                self.assertEqual(config.read_bytes(), original_config)
                run("vibemon", uninstall=True)
                run("dotfiles")
                verify(installed=False)
                self.assertEqual(config.read_bytes(), original_config)
                run("vibemon")
                verify()
                self.assertEqual(config.read_bytes(), original_config)


if __name__ == "__main__":
    unittest.main()
