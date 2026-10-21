#!/usr/bin/env python3
"""Offline tests for lib/core.sh: retries, downloads, file installation and state."""

import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parent.parent


class CoreTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="dot-core-")
        self.addCleanup(temporary.cleanup)
        self.home = Path(temporary.name) / "home"
        self.repo = self.home / ".dotfiles"
        self.repo.mkdir(parents=True)
        self.env = {key: value for key, value in os.environ.items() if not key.startswith("BASH_FUNC_")}
        for key in ("DOT_HOME", "DOT_CONFIG", "DOT_STATE", "DOT_FORCE", "XDG_CONFIG_HOME", "XDG_STATE_HOME"):
            self.env.pop(key, None)
        self.env.update(HOME=str(self.home), DOT_HOME=str(self.repo), DOT_COLOR="false",
                        TERM="dumb", BASH_ENV="")

    def run_shell(self, body, **env):
        script = '. "$CORE"\nsleep() { :; }\n' + body
        return subprocess.run(["/bin/bash", "-c", script], env=dict(self.env, CORE=str(ROOT / "lib/core.sh"), **env),
                              capture_output=True, text=True, timeout=10)

    # dot_retry

    def test_retry_preserves_diagnostics_and_stops_after_three_attempts(self):
        result = self.run_shell('''
sleep() { printf '%s\\n' "$1" >> "$HOME/waits"; }
operation() { printf 'network failure\\n' >&2; return 7; }
dot_retry "Operation" operation
''')
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(result.stderr.splitlines(), ["network failure"] * 3)
        self.assertEqual((self.home / "waits").read_text().splitlines(), ["5", "10"])

    def test_retry_stops_at_first_success(self):
        result = self.run_shell('''
calls=0
operation() { calls=$((calls + 1)); [ "$calls" -eq 2 ]; }
dot_retry "Operation" operation || exit 1
printf 'attempts=%s\\n' "$calls"
''')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("attempts=2", result.stdout)

    # dot_install_script

    def test_partial_download_is_never_executed(self):
        staging = self.home / "staging"
        staging.mkdir()
        result = self.run_shell('''
curl() {
  while [ "$1" != -o ]; do shift; done
  printf 'touch "$HOME/partial-executed"\\n' > "$2"
  return 22
}
dot_install_script https://example.invalid/install.sh
''', TMPDIR=str(staging))
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse((self.home / "partial-executed").exists())
        self.assertEqual(list(staging.iterdir()), [])

    def test_script_requires_valid_syntax_and_cleans_staging(self):
        staging = self.home / "staging"
        staging.mkdir()
        for payload, succeeds in (('touch "$HOME/bootstrap-ran"', True),
                                  ('touch "$HOME/bootstrap-ran"; if', False)):
            with self.subTest(payload=payload):
                marker = self.home / "bootstrap-ran"
                marker.unlink(missing_ok=True)
                result = self.run_shell('''
curl() {
  while [ "$1" != -o ]; do shift; done
  printf '%s\\n' "$PAYLOAD" > "$2"
}
dot_install_script https://example.invalid/install.sh
''', TMPDIR=str(staging), PAYLOAD=payload)
                self.assertEqual(result.returncode == 0, succeeds, result.stderr)
                self.assertEqual(marker.exists(), succeeds)
                self.assertEqual(list(staging.iterdir()), [])

    def test_script_preserves_environment_arguments_and_status(self):
        staging = self.home / "staging"
        staging.mkdir()
        result = self.run_shell('''
curl() {
  while [ "$1" != -o ]; do shift; done
  cat > "$2" <<'SCRIPT'
printf '<%s>\\n' "$RUNZSH" "$@" > "$HOME/arguments"
exit 17
SCRIPT
}
RUNZSH=no dot_install_script https://example.invalid/install.sh 'one two' '' '*'
''', TMPDIR=str(staging))
        self.assertEqual(result.returncode, 17, result.stderr)
        self.assertEqual((self.home / "arguments").read_text().splitlines(),
                         ["<no>", "<one two>", "<>", "<*>"])
        self.assertEqual(list(staging.iterdir()), [])

    # dot_install_file

    def install(self, target=".settings", source="settings", prelude=""):
        return self.run_shell(prelude + f'dot_install_file "{target}" "{source}"\n')

    def test_install_backs_up_and_is_idempotent(self):
        (self.repo / "settings").write_text("new")
        target = self.home / ".settings"
        target.write_text("previous")
        first = self.install()
        self.assertEqual(first.returncode, 0, first.stderr)
        self.assertEqual(target.read_text(), "new")
        backup = self.home / ".settings.backup"
        self.assertEqual(backup.read_text(), "previous")
        self.assertEqual(backup.stat().st_mode & 0o777, 0o600)
        stamp = target.stat().st_mtime_ns
        second = self.install()
        self.assertEqual(second.returncode, 0, second.stderr)
        self.assertEqual(second.stdout, "")
        self.assertEqual(target.stat().st_mtime_ns, stamp)
        self.assertEqual(backup.read_text(), "previous")

    def test_missing_source_fails_without_changes(self):
        target = self.home / ".settings"
        target.write_text("working")
        result = self.install()
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(target.read_text(), "working")

    def test_failures_preserve_destination_and_backup(self):
        cases = {
            "copy": 'cp() { return 1; }\n',
            "replace": 'mv() { case "$2" in *.backup) command mv "$@" ;; *) return 1 ;; esac; }\n',
            "backup": '''cp() {
  case "$2" in "$HOME/.settings.backup"*) printf partial > "$2"; return 7 ;; esac
  command cp "$@"
}
''',
            "checksum": 'dot_md5() { return 7; }\n',
        }
        for name, prelude in cases.items():
            with self.subTest(failure=name):
                (self.repo / "settings").write_text("new")
                target = self.home / ".settings"
                target.write_text("working")
                backup = self.home / ".settings.backup"
                backup.write_text("earlier backup")
                result = self.install(prelude=prelude)
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(target.read_text(), "working")
                self.assertEqual(backup.read_text(), "earlier backup")
                self.assertEqual(list(self.home.glob(".settings*.tmp.*")), [])

    def test_directory_target_is_rejected(self):
        (self.repo / "settings").write_text("new")
        target = self.home / ".settings"
        target.mkdir()
        result = self.install()
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(list(target.iterdir()), [])

    def test_non_regular_backup_blocks_replacement(self):
        (self.repo / "settings").write_text("new")
        target = self.home / ".settings"
        target.write_text("working")
        backup = self.home / ".settings.backup"
        victim = self.home / "unrelated"
        victim.write_text("unrelated data")
        for kind in ("directory", "symlink"):
            with self.subTest(kind=kind):
                if kind == "directory":
                    backup.mkdir(mode=0o755)
                else:
                    backup.symlink_to(victim)
                result = self.install()
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(target.read_text(), "working")
                self.assertEqual(victim.read_text(), "unrelated data")
                if kind == "directory":
                    self.assertEqual(list(backup.iterdir()), [])
                    backup.rmdir()
                else:
                    self.assertTrue(backup.is_symlink())
                self.assertEqual(list(self.home.glob(".settings*.tmp.*")), [])

    def test_backup_replacement_does_not_modify_other_hardlinks(self):
        (self.repo / "settings").write_text("new")
        target = self.home / ".settings"
        target.write_text("working")
        other = self.home / "other"
        other.write_text("unrelated data")
        os.link(other, self.home / ".settings.backup")
        result = self.install()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(target.read_text(), "new")
        self.assertEqual((self.home / ".settings.backup").read_text(), "working")
        self.assertEqual(other.read_text(), "unrelated data")

    def test_private_paths_get_mode_600_and_spaces_work(self):
        (self.repo / "config with spaces").write_text("settings")
        for target in (".ssh/config with spaces", ".aws/config with spaces"):
            with self.subTest(target=target):
                result = self.install(target, "config with spaces")
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual((self.home / target).read_text(), "settings")
                self.assertEqual((self.home / target).stat().st_mode & 0o777, 0o600)

    def test_explicit_mode_is_applied(self):
        (self.repo / "settings").write_text("x")
        result = self.run_shell('dot_install_file .settings settings 640\n')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual((self.home / ".settings").stat().st_mode & 0o777, 0o640)

    # dot_same_file and dot_md5

    def test_same_file_reports_equal_different_and_failure(self):
        (self.home / "a").write_text("one")
        (self.home / "b").write_text("one")
        (self.home / "c").write_text("two")
        result = self.run_shell('''
dot_same_file "$HOME/a" "$HOME/b"; printf '%s\\n' $?
dot_same_file "$HOME/a" "$HOME/c"; printf '%s\\n' $?
dot_same_file "$HOME/a" "$HOME/missing"; printf '%s\\n' $?
dot_md5() { return 7; }
dot_same_file "$HOME/a" "$HOME/b"; printf '%s\\n' $?
dot_md5() { printf ''; }
dot_same_file "$HOME/a" "$HOME/b"; printf '%s\\n' $?
''')
        self.assertEqual(result.stdout.split(), ["0", "1", "1", "2", "2"])

    def test_md5_failure_propagates(self):
        result = self.run_shell('md5sum() { return 7; }\nmd5() { return 7; }\ndot_md5 "$HOME"\n')
        self.assertEqual(result.returncode, 7)

    # State

    def test_due_and_stamp(self):
        stamps = self.home / ".local/state/dotfiles/stamps"
        result = self.run_shell('dot_due brew && printf due\n')
        self.assertEqual(result.stdout, "due")
        for content in ("", "not-a-number\n", "0\n"):
            with self.subTest(content=content):
                stamps.mkdir(parents=True, exist_ok=True)
                (stamps / "brew").write_text(content)
                self.assertEqual(self.run_shell('dot_due brew && printf due\n').stdout, "due")
        result = self.run_shell('dot_stamp brew && dot_due brew || printf fresh\n')
        self.assertEqual(result.stdout, "fresh")
        self.assertEqual(self.run_shell('dot_due brew && printf due\n', DOT_FORCE="true").stdout, "due")
        self.assertIn("m ago", self.run_shell('dot_stamp_age brew\n').stdout)
        self.assertEqual(self.run_shell('dot_stamp_age never-run\n').stdout, "never")

    def test_applied_marker_tracks_successful_content(self):
        source = self.home / "defaults.sh"
        source.write_text("v1")
        result = self.run_shell(f'''
dot_applied "{source}" key && printf yes || printf no
dot_mark_applied "{source}" key
dot_applied "{source}" key && printf yes || printf no
printf v2 > "{source}"
dot_applied "{source}" key && printf yes || printf no
''')
        self.assertEqual(result.stdout, "noyesno")

    def test_warnings_are_counted_in_the_shared_file(self):
        warnings = self.home / "warnings"
        result = self.run_shell('( dot_warn first ); dot_warn second\n', DOT_WARN_FILE=str(warnings))
        self.assertEqual(result.returncode, 0)
        self.assertEqual(warnings.read_text().splitlines(), ["first", "second"])
        self.assertIn("⚠ first", result.stdout)

    def test_local_env_is_exported(self):
        config = self.home / ".config/dotfiles"
        config.mkdir(parents=True)
        (config / "local.env").write_text("DOT_TIMEZONE=UTC\n")
        result = self.run_shell('dot_load_local_env; bash -c \'printf "%s" "$DOT_TIMEZONE"\'\n')
        self.assertEqual(result.stdout, "UTC")

    def test_memory_helper_reads_meminfo(self):
        root = self.home / "sysroot"
        (root / "proc").mkdir(parents=True)
        (root / "proc/meminfo").write_text("MemTotal: 1 kB\nMemAvailable:   12582912 kB\n")
        result = self.run_shell('dot_mem_available_gib\n', DOT_SYSROOT=str(root))
        self.assertEqual(result.stdout.strip(), "12")


if __name__ == "__main__":
    unittest.main()
