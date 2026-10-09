#!/usr/bin/env python3
"""Offline checks for shell startup PATH construction."""

import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parent.parent


class ShellStartupTests(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
