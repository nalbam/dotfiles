#!/usr/bin/env python3
"""Offline macOS setup regressions; never changes preferences or closes real apps."""

import os
from pathlib import Path
import signal
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parent.parent


class MacOSSetupTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="dotfiles-macos-")
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name) / "machine-home"
        self.repo = self.home / ".dotfiles"
        self.repo.mkdir(parents=True)
        (self.home / ".toast").mkdir()
        bindings = self.home / "Library/KeyBindings"
        bindings.mkdir(parents=True)
        (bindings / "DefaultkeyBinding.dict").touch()
        shutil.copy(ROOT / "macos", self.repo / "macos")
        self.marker = self.home / ".toast/macos.applied"
        self.log = self.home / "commands"
        self.env = dict(os.environ, HOME=str(self.home), TERM="dumb")
        source = (ROOT / "run.sh").read_text()
        declarations = source[:source.index("# 실행 영역 (Execution Section)")] + "\n}\n"
        step = source[source.index("# Step 7:"):source.index("# Step 8:")]
        # Use the real installer helpers and Step 7, mocking only OS commands.
        self.script = declarations + r'''
OS_NAME="${TEST_OS_NAME:-darwin}"
OS_ARCH="${TEST_OS_ARCH:-arm64}"
TPUT=
export TEST_INSTALLER_PID=$$
_md5() { cksum < "$1"; }
xcode-select() { return 0; }
pgrep() { return 0; }
curl() { printf 'Unexpected network request\n' >&2; return 1; }
cp() {
  if [ "${TEST_MARKER_STATUS:-0}" != 0 ] && [ "$2" = "$HOME/.toast/macos.applied" ]; then
    return 1
  fi
  command cp "$@"
}
osascript() { printf 'osascript %s\n' "$*" >> "$HOME/commands"; }
sudo() {
  printf 'sudo %s\n' "$*" >> "$HOME/commands"
  return "${TEST_SUDO_STATUS:-0}"
}
defaults() {
  printf 'defaults %s\n' "$*" >> "$HOME/commands"
  if [ "${TEST_INTERRUPT:-0}" = 1 ]; then
    kill -HUP "$TEST_INSTALLER_PID"
    return 1
  fi
  return "${TEST_DEFAULTS_STATUS:-0}"
}
chflags() { printf 'chflags %s\n' "$*" >> "$HOME/commands"; }
killall() {
  printf 'killall %s\n' "$*" >> "$HOME/commands"
  # Model losing the terminal by signaling only this test's installer shell.
  if [ "$1" = Terminal ]; then kill -HUP "$TEST_INSTALLER_PID"; fi
}
# End the mocked sudo keep-alive immediately, without a background sleep.
sleep() { exit 0; }
export -f osascript sudo defaults chflags killall sleep
''' + step + '\nprintf "NEXT_STEP\\n"\n'

    def invoke(self, **overrides):
        return subprocess.run(["/bin/bash", "-c", self.script],
                              env=dict(self.env, **overrides), cwd=self.temp.name,
                              capture_output=True, text=True, timeout=5)

    def assert_continues(self, result):
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("NEXT_STEP", result.stdout)

    def test_fresh_install_keeps_terminal_alive_and_repeat_skips_preferences(self):
        for arch in ("arm64", "x86_64"):
            with self.subTest(arch=arch):
                self.marker.unlink(missing_ok=True)
                self.log.unlink(missing_ok=True)
                self.assert_continues(self.invoke(TEST_OS_ARCH=arch))
                self.assertEqual(self.marker.read_bytes(), (self.repo / "macos").read_bytes())
                calls = self.log.read_text()
                self.assertIn("defaults write", calls)
                self.assertNotIn("killall", calls)
                self.assertEqual(self.marker.stat().st_mode & 0o777, 0o600)
                stamp = self.marker.stat().st_mtime_ns
                self.assert_continues(self.invoke(TEST_OS_ARCH=arch))
                self.assertEqual(self.marker.stat().st_mtime_ns, stamp)
                self.assertEqual(self.log.read_text(), calls)

    def test_download_backup_does_not_count_as_success(self):
        previous = "#!/bin/bash\necho old preferences\n"
        (self.home / ".macos").write_text(previous)
        self.assert_continues(self.invoke())
        self.assertIn("defaults write", self.log.read_text())
        self.assertEqual((self.home / ".macos.backup").read_text(), previous)
        self.assertEqual(self.marker.read_bytes(), (self.repo / "macos").read_bytes())

    def test_legacy_backup_without_completion_marker_reapplies(self):
        shutil.copy(self.repo / "macos", self.home / ".macos")
        shutil.copy(self.repo / "macos", self.home / ".macos.backup")
        self.assert_continues(self.invoke())
        self.assertIn("defaults write", self.log.read_text())
        self.assertTrue(self.marker.exists())

    def test_authentication_and_preference_failures_retry(self):
        for failure in ("TEST_SUDO_STATUS", "TEST_DEFAULTS_STATUS"):
            with self.subTest(failure=failure):
                self.marker.unlink(missing_ok=True)
                self.log.unlink(missing_ok=True)
                result = self.invoke(**{failure: "1"})
                self.assert_continues(result)
                self.assertFalse(self.marker.exists())
                self.assertIn("macOS system preferences failed", result.stdout)
                self.assertNotIn("macOS system preferences applied", result.stdout)
                if failure == "TEST_SUDO_STATUS":
                    self.assertNotIn("defaults write", self.log.read_text())
                self.assert_continues(self.invoke())
                self.assertTrue(self.marker.exists())

    def test_changed_preferences_failed_apply_preserves_marker_and_retries(self):
        self.assert_continues(self.invoke())
        previous = self.marker.read_bytes()
        source = self.repo / "macos"
        source.write_text(source.read_text() + '\ndefaults write test.retry enabled -bool true\n')
        result = self.invoke(TEST_DEFAULTS_STATUS="1")
        self.assert_continues(result)
        self.assertEqual(self.marker.read_bytes(), previous)
        self.assert_continues(self.invoke())
        self.assertEqual(self.marker.read_bytes(), source.read_bytes())
        self.assertIn("defaults write test.retry enabled -bool true", self.log.read_text())

    def test_interrupted_install_retries_without_completion_marker(self):
        result = self.invoke(TEST_INTERRUPT="1")
        self.assertEqual(result.returncode, -signal.SIGHUP)
        self.assertFalse(self.marker.exists())
        self.assert_continues(self.invoke())
        self.assertTrue(self.marker.exists())

    def test_failed_completion_record_warns_and_retries(self):
        result = self.invoke(TEST_MARKER_STATUS="1")
        self.assert_continues(result)
        self.assertIn("Failed to record macOS system preferences", result.stdout)
        self.assertNotIn("macOS system preferences applied", result.stdout)
        self.assertFalse(self.marker.exists())
        calls = self.log.read_text()
        self.assert_continues(self.invoke())
        self.assertTrue(self.marker.exists())
        self.assertGreater(len(self.log.read_text()), len(calls))

    def test_linux_skips_macos_preferences(self):
        self.assert_continues(self.invoke(TEST_OS_NAME="linux", TEST_OS_ARCH="x86_64"))
        self.assertFalse(self.log.exists())
        self.assertFalse(self.marker.exists())
        self.assertFalse((self.home / ".macos").exists())


if __name__ == "__main__":
    unittest.main()
