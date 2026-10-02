#!/usr/bin/env python3
"""Offline macOS setup regressions; never changes preferences or closes real apps."""

import fcntl
import os
from pathlib import Path
import signal
import shutil
import subprocess
import tempfile
import termios
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
  if [ "${TEST_SUDO_STATUS:-0}" != 0 ]; then return "$TEST_SUDO_STATUS"; fi
  if [ "$1" = nvram ]; then shift; nvram "$@"; fi
}
nvram() {
  printf 'nvram %s\n' "$*" >> "$HOME/commands"
  if [ "$1" = StartupMute ]; then
    if [ "${TEST_NVRAM_READ_STATUS:-0}" != 0 ]; then return "$TEST_NVRAM_READ_STATUS"; fi
    printf 'StartupMute\t%s\n' "${TEST_STARTUP_MUTE:-%01}"
  elif [ "$1" = StartupMute=%01 ]; then
    return "${TEST_NVRAM_WRITE_STATUS:-0}"
  else
    return 1
  fi
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
sysadminctl() {
  printf 'sysadminctl %s\n' "$*" >> "$HOME/commands"
  if [ "$1" != -screenLock ]; then return 1; fi
  if [ "$2" = status ]; then
    if [ -f "$HOME/screen-lock-immediate" ]; then
      printf 'screenLock delay is immediate\n' >&2
      return "${TEST_SCREEN_LOCK_VERIFY_STATUS:-0}"
    fi
    printf 'screenLock delay is %s\n' "${TEST_SCREEN_LOCK_DELAY:-immediate}" >&2
    return "${TEST_SCREEN_LOCK_STATUS:-0}"
  fi
  if [ "$2" != immediate ] || [ "$3" != -password ] || [ "$4" != - ]; then
    return 1
  fi
  # sysadminctl reads stdin instead of opening /dev/tty for piped installers.
  if [ ! -t 0 ]; then
    printf 'Password is required!\n' >&2
    return 0
  fi
  if [ "${TEST_SCREEN_LOCK_SET_STATUS:-0}" != 0 ]; then
    return "$TEST_SCREEN_LOCK_SET_STATUS"
  fi
  if [ "${TEST_SCREEN_LOCK_NO_CHANGE:-0}" = 0 ]; then
    touch "$HOME/screen-lock-immediate"
  fi
}
killall() {
  printf 'killall %s\n' "$*" >> "$HOME/commands"
  # Model losing the terminal by signaling only this test's installer shell.
  if [ "$1" = Terminal ]; then kill -HUP "$TEST_INSTALLER_PID"; fi
}
export -f osascript sudo nvram defaults chflags sysadminctl killall
''' + step + '\nprintf "NEXT_STEP\\n"\n'

    def invoke(self, *, terminal=True, **overrides):
        master, slave = os.openpty() if terminal else (None, None)

        def attach_terminal():
            os.setsid()
            if terminal:
                fcntl.ioctl(slave, termios.TIOCSCTTY, 0)

        try:
            # Feed the installer through a pipe, as in curl | bash. A controlling
            # terminal remains available for authentication unless disabled.
            return subprocess.run(["/bin/bash"], input=self.script,
                                  env=dict(self.env, **overrides), cwd=self.temp.name,
                                  capture_output=True, text=True, timeout=5,
                                  preexec_fn=attach_terminal,
                                  pass_fds=(slave,) if terminal else ())
        finally:
            if terminal:
                os.close(master)
                os.close(slave)

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
        for failure in ("TEST_SUDO_STATUS", "TEST_NVRAM_WRITE_STATUS", "TEST_DEFAULTS_STATUS"):
            with self.subTest(failure=failure):
                self.marker.unlink(missing_ok=True)
                self.log.unlink(missing_ok=True)
                result = self.invoke(TEST_STARTUP_MUTE="%00", **{failure: "1"})
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

    def test_immediate_screen_lock_does_not_prompt_for_password(self):
        self.assert_continues(self.invoke(terminal=False))
        calls = self.log.read_text()
        self.assertIn("sysadminctl -screenLock status", calls)
        self.assertNotIn("sysadminctl -screenLock immediate", calls)
        self.assertNotIn("sudo", calls)

    def test_startup_sound_authenticates_only_when_mute_is_needed(self):
        for overrides in ({"TEST_STARTUP_MUTE": "%00"}, {"TEST_NVRAM_READ_STATUS": "1"}):
            with self.subTest(overrides=overrides):
                self.marker.unlink(missing_ok=True)
                self.log.unlink(missing_ok=True)
                self.assert_continues(self.invoke(**overrides))
                calls = self.log.read_text()
                self.assertEqual(calls.count("sudo "), 1)
                self.assertIn("sudo nvram StartupMute=%01", calls)

    def test_screen_lock_without_terminal_reports_action_and_retries(self):
        result = self.invoke(terminal=False, TEST_SCREEN_LOCK_DELAY="60 seconds")
        self.assert_continues(result)
        self.assertIn("terminal", result.stderr)
        self.assertIn("Lock Screen", result.stderr)
        self.assertFalse(self.marker.exists())
        self.assertNotIn("sysadminctl -screenLock immediate", self.log.read_text())
        self.assert_continues(self.invoke(TEST_SCREEN_LOCK_DELAY="60 seconds"))
        self.assertTrue(self.marker.exists())

    def test_screen_lock_change_is_verified_before_recording_success(self):
        self.assert_continues(self.invoke(TEST_SCREEN_LOCK_DELAY="60 seconds"))
        calls = self.log.read_text()
        self.assertIn("sysadminctl -screenLock immediate -password -", calls)
        self.assertEqual(calls.count("sysadminctl -screenLock status"), 2)
        self.assertTrue((self.home / "screen-lock-immediate").exists())
        self.assertTrue(self.marker.exists())
        self.assert_continues(self.invoke())
        self.assertEqual(self.log.read_text(), calls)

    def test_screen_lock_failures_do_not_record_success_and_retry(self):
        for failure in ("TEST_SCREEN_LOCK_STATUS", "TEST_SCREEN_LOCK_SET_STATUS",
                        "TEST_SCREEN_LOCK_NO_CHANGE", "TEST_SCREEN_LOCK_VERIFY_STATUS"):
            with self.subTest(failure=failure):
                self.marker.unlink(missing_ok=True)
                (self.home / "screen-lock-immediate").unlink(missing_ok=True)
                result = self.invoke(TEST_SCREEN_LOCK_DELAY="60 seconds", **{failure: "1"})
                self.assert_continues(result)
                self.assertFalse(self.marker.exists())
                self.assertIn("macOS system preferences failed", result.stdout)
                self.assertNotIn("macOS system preferences applied", result.stdout)
                self.assert_continues(self.invoke(TEST_SCREEN_LOCK_DELAY="60 seconds"))
                self.assertTrue(self.marker.exists())

    def test_linux_skips_macos_preferences(self):
        self.assert_continues(self.invoke(TEST_OS_NAME="linux", TEST_OS_ARCH="x86_64"))
        self.assertFalse(self.log.exists())
        self.assertFalse(self.marker.exists())
        self.assertFalse((self.home / ".macos").exists())


if __name__ == "__main__":
    unittest.main()
