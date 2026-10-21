#!/usr/bin/env python3
"""Run shell helpers against fake tools without modifying a real profile."""

import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parent.parent
SHELLS = [shell for shell in ("/bin/bash", "/bin/zsh") if Path(shell).is_file()]


class AliasTests(unittest.TestCase):
    def run_shell(self, shell, body):
        with tempfile.TemporaryDirectory(prefix="dotfiles-aliases-") as temporary:
            home = Path(temporary)
            env = dict(os.environ, HOME=str(home), PATH="/usr/bin:/bin",
                       BASH_ENV="", ENV="", ZDOTDIR=str(home))
            args = ["--noprofile", "--norc"] if shell.endswith("bash") else ["-f"]
            prefix = "shopt -s expand_aliases\n" if shell.endswith("bash") else ""
            return subprocess.run(
                [shell, *args, "-c", prefix + '. "$1"\n' + body,
                 "aliases-test", str(ROOT / "aliases")],
                cwd=home, env=env, capture_output=True, text=True, timeout=5,
            )

    def test_workspace_arguments_and_failure(self):
        for shell in SHELLS:
            with self.subTest(shell=shell):
                result = self.run_shell(shell, '''
toast() { printf '<%s>\\n' "$@" >&2; return 17; }
c "one two" "" "*"
''')
                self.assertEqual(result.returncode, 17, result.stderr)
                self.assertEqual(result.stderr.splitlines(), ["<cdw>", "<one two>", "<>", "<*>"])
                self.assertEqual(result.stdout, "")

    def test_aws_identity_failure_stops_followup(self):
        for shell in SHELLS:
            with self.subTest(shell=shell):
                result = self.run_shell(shell, '''
aws() { return 23; }
eval 'm && printf "unexpected followup"'
''')
                self.assertEqual(result.returncode, 23, result.stderr)
                self.assertEqual(result.stdout, "")

    def test_aws_identity_disables_pager(self):
        for shell in SHELLS:
            with self.subTest(shell=shell):
                result = self.run_shell(shell, '''
aws() { printf '<%s>\\n' "$@"; }
eval 'm'
''')
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(result.stdout.splitlines(),
                                 ["<sts>", "<get-caller-identity>", "<--output>",
                                  "<json>", "<--no-cli-pager>"])

    def test_vault_shortcuts_preserve_arguments(self):
        for shell in SHELLS:
            for shortcut, profile in (("n", "nalbam"), ("two", "nalbam-two"),
                                      ("k", "awskrug-team"), ("ops", "opspresso")):
                with self.subTest(shell=shell, shortcut=shortcut):
                    result = self.run_shell(shell, '''
aws-vault() { printf '<%s>\\n' "$@"; return 19; }
av ''' + shortcut + ''' printf '%s' 'one two' '' '*'
''')
                    self.assertEqual(result.returncode, 19, result.stderr)
                    self.assertEqual(result.stdout.splitlines(),
                                     ["<exec>", f"<{profile}>", "<-->", "<printf>",
                                      "<%s>", "<one two>", "<>", "<*>"])

    def test_vault_list_failure_does_not_offer_invented_profiles(self):
        for shell in SHELLS:
            with self.subTest(shell=shell):
                result = self.run_shell(shell, '''
aws-vault() { return 13; }
fzf() { printf 'unexpected selection'; }
av
''')
                self.assertEqual(result.returncode, 13, result.stderr)
                self.assertEqual(result.stdout, "")


if __name__ == "__main__":
    unittest.main()
