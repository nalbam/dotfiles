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
        (self.repo / "config").mkdir(parents=True)
        shutil.copytree(ROOT / "config/macos", self.repo / "config/macos")
        self.source = self.repo / "config/macos/defaults.sh"
        bindings = self.home / "Library/KeyBindings"
        bindings.mkdir(parents=True)
        self.binding = bindings / "DefaultkeyBinding.dict"
        self.binding.write_text("personal binding\n")
        self.marker = self.home / ".local/state/dotfiles/applied/macos-defaults"
        self.log = self.home / "commands"
        self.env = {key: value for key, value in os.environ.items()
                    if not key.startswith(("XDG_", "DOT_", "BASH_FUNC_"))}
        self.env.update(HOME=str(self.home), TERM="dumb", DOT_HOME=str(self.repo), DOT_COLOR="false")
        # Use the real dot helpers and macos module, mocking only OS commands.
        self.script = f'''
. "{ROOT}/lib/core.sh"
. "{ROOT}/lib/detect.sh"
. "{ROOT}/lib/modules.sh"
. "{ROOT}/modules/macos.sh"
DOT_PLATFORM="${{TEST_PLATFORM:-macos}}"
DOT_OS=darwin
DOT_ARCH="${{TEST_OS_ARCH:-arm64}}"
''' + r'''
export TEST_INSTALLER_PID=$$
dot_load_paths() { :; }
dot_md5() {
  if [ "${TEST_MARKER_HASH_FAILURE:-0}" = 1 ] && [ "$1" = "$DOT_STATE/applied/macos-defaults" ]; then
    return 7
  fi
  cksum < "$1"
}
xcode-select() {
  [ "$1" = -p ] && return "${TEST_CLT_STATUS:-0}"
  printf 'xcode-select %s\n' "$*" >> "$HOME/commands"
}
pgrep() { return "${TEST_ROSETTA_STATUS:-0}"; }
softwareupdate() { printf 'softwareupdate %s\n' "$*" >> "$HOME/commands"; }
curl() { printf 'Unexpected network request\n' >&2; return 1; }
mv() {
  if [ "${TEST_MARKER_STATUS:-0}" != 0 ] && [ "${!#}" = "$DOT_STATE/applied/macos-defaults" ]; then
    return 1
  fi
  command mv "$@"
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
dot_module_run macos || exit
printf "NEXT_STEP\n"
'''

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
                self.assertEqual(self.marker.read_bytes(), self.source.read_bytes())
                calls = self.log.read_text()
                self.assertIn("defaults write", calls)
                self.assertNotIn("killall", calls)
                self.assertEqual(self.marker.stat().st_mode & 0o777, 0o600)
                stamp = self.marker.stat().st_mtime_ns
                self.assert_continues(self.invoke(TEST_OS_ARCH=arch))
                self.assertEqual(self.marker.stat().st_mtime_ns, stamp)
                self.assertEqual(self.log.read_text(), calls)

    def test_unreadable_completion_hash_stops_without_applying(self):
        self.marker.parent.mkdir(parents=True)
        self.marker.write_text("previous successful preferences\n")
        result = self.invoke(TEST_MARKER_HASH_FAILURE="1")
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertNotIn("already applied", result.stdout)
        self.assertIn("Failed to compare system preferences", result.stdout + result.stderr)
        self.assertEqual(self.marker.read_text(), "previous successful preferences\n")
        self.assertFalse(self.log.exists() and "defaults write" in self.log.read_text())

    def test_authentication_and_preference_failures_retry(self):
        for failure in ("TEST_SUDO_STATUS", "TEST_NVRAM_WRITE_STATUS", "TEST_DEFAULTS_STATUS"):
            with self.subTest(failure=failure):
                self.marker.unlink(missing_ok=True)
                self.log.unlink(missing_ok=True)
                result = self.invoke(TEST_STARTUP_MUTE="%00", **{failure: "1"})
                self.assert_continues(result)
                self.assertFalse(self.marker.exists())
                self.assertIn("System preferences failed", result.stdout)
                self.assertNotIn("System preferences applied", result.stdout)
                if failure == "TEST_SUDO_STATUS":
                    self.assertNotIn("defaults write", self.log.read_text())
                self.assert_continues(self.invoke())
                self.assertTrue(self.marker.exists())

    def test_changed_preferences_failed_apply_preserves_marker_and_retries(self):
        self.assert_continues(self.invoke())
        previous = self.marker.read_bytes()
        source = self.source
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

    def test_failed_completion_record_retries(self):
        result = self.invoke(TEST_MARKER_STATUS="1")
        self.assert_continues(result)
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
                self.assertIn("System preferences failed", result.stdout)
                self.assertNotIn("System preferences applied", result.stdout)
                self.assert_continues(self.invoke(TEST_SCREEN_LOCK_DELAY="60 seconds"))
                self.assertTrue(self.marker.exists())

    def test_other_platforms_skip_the_module(self):
        result = self.invoke(TEST_PLATFORM="linux", TEST_OS_ARCH="x86_64")
        self.assert_continues(result)
        self.assertIn("not supported on linux", result.stdout)
        self.assertFalse(self.log.exists())
        self.assertFalse(self.marker.exists())

    def test_missing_command_line_tools_start_installer_and_warn(self):
        result = self.invoke(TEST_CLT_STATUS="1")
        self.assert_continues(result)
        self.assertIn("xcode-select --install", self.log.read_text())
        self.assertIn("Command Line Tools", result.stdout)
        self.assertTrue(self.marker.exists())

    def test_rosetta_is_installed_only_on_arm64_when_missing(self):
        for arch, status, expected in (("arm64", "1", True), ("arm64", "0", False), ("x86_64", "1", False)):
            with self.subTest(arch=arch, status=status):
                self.log.unlink(missing_ok=True)
                self.assert_continues(self.invoke(TEST_OS_ARCH=arch, TEST_ROSETTA_STATUS=status))
                calls = self.log.read_text() if self.log.exists() else ""
                self.assertEqual("--install-rosetta" in calls, expected)

    def test_key_binding_is_copied_once_and_local_edits_survive(self):
        self.binding.unlink()
        self.assert_continues(self.invoke())
        source = self.repo / "config/macos/DefaultkeyBinding.dict"
        self.assertEqual(self.binding.read_bytes(), source.read_bytes())
        self.binding.write_text("edited\n")
        self.assert_continues(self.invoke())
        self.assertEqual(self.binding.read_text(), "edited\n")



if __name__ == "__main__":
    unittest.main()
