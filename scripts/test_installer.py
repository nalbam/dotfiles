#!/usr/bin/env python3
"""Offline regression tests for the Bash installer's file and package operations."""

import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parent.parent


class InstallerTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="dotfiles-installer-")
        self.addCleanup(temporary.cleanup)
        self.home = Path(temporary.name) / "home"
        self.repo = self.home / ".dotfiles"
        self.repo.mkdir(parents=True)
        self.source = (ROOT / "run.sh").read_text()
        self.declarations = self.source.split("# 실행 영역", 1)[0] + "\n}\nTPUT=\ncurl() { return 99; }\nsleep() { :; }\n"
        self.env = dict(os.environ, HOME=str(self.home), TERM="dumb", BASH_ENV="")

    def run_shell(self, body):
        return subprocess.run(["/bin/bash", "-c", self.declarations + body],
                              env=self.env, capture_output=True, text=True, timeout=5)

    def block(self, start, end):
        execution = self.source[self.source.index("# 실행 영역"):]
        return execution[execution.index(start):execution.index(end)]

    def test_every_git_identity_include_is_deployed_and_effective(self):
        for source in ROOT.glob("gitconfig*"):
            shutil.copy(source, self.repo / source.name)
        result = self.run_shell(self.block("# Git 설정 파일 다운로드", "# Step 5:"))
        self.assertEqual(result.returncode, 0, result.stderr)
        for account, profile in [("nalbam", "nalbam"), ("opspresso", "nalbam"),
                                 ("yujh404", "yujh404"), ("nalbam-me", "nalbam-me"),
                                 ("nalbam-bot", "nalbam-bot")]:
            with self.subTest(account=account):
                target = self.home / (".gitconfig-" + profile)
                self.assertTrue(target.is_file(), f"Missing identity profile: {profile}")
                workspace = self.home / "workspace/github.com" / account / "example"
                subprocess.run(["git", "init", "-q", str(workspace)], env=self.env, check=True)
                for key in ("user.name", "user.email"):
                    actual = subprocess.check_output(["git", "-C", str(workspace), "config", "--get", key], env=self.env)
                    expected = subprocess.check_output(["git", "config", "--file", str(ROOT / ("gitconfig-" + profile)), "--get", key], env=self.env)
                    self.assertTrue(actual == expected, f"Incorrect {key} for {profile}")

    def test_failed_download_preserves_config_and_backup(self):
        target = self.home / ".settings"
        target.write_text("working configuration")
        backup = target.with_name(target.name + ".backup")
        backup.write_text("earlier backup")
        result = self.run_shell('''
sleep() { :; }
curl() {
  while [ "$1" != "-o" ]; do shift; done
  printf "partial transfer" > "$2"
  printf "attempt\\n" >> "$HOME/attempts"
  return 22
}
_download .settings absent-source
''')
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(target.read_text(), "working configuration")
        self.assertEqual(backup.read_text(), "earlier backup")
        self.assertEqual((self.home / "attempts").read_text().splitlines(), ["attempt"] * 3)
        self.assertEqual(list(self.home.glob(".settings.tmp.*")), [])

    def test_successful_download_backs_up_and_is_idempotent(self):
        target = self.home / ".settings"
        target.write_text("previous")
        body = '''
curl() {
  while [ "$1" != "-o" ]; do shift; done
  printf "complete transfer" > "$2"
}
_download .settings absent-source
'''
        first = self.run_shell(body)
        self.assertEqual(first.returncode, 0, first.stderr)
        self.assertEqual(target.read_text(), "complete transfer")
        self.assertEqual(target.with_name(target.name + ".backup").read_text(), "previous")
        stamp = target.stat().st_mtime_ns
        second = self.run_shell(body)
        self.assertEqual(second.returncode, 0, second.stderr)
        self.assertEqual(target.stat().st_mtime_ns, stamp)
        self.assertEqual(target.with_name(target.name + ".backup").read_text(), "previous")

    def test_copy_failure_is_not_reported_as_success(self):
        (self.repo / "settings").write_text("new")
        target = self.home / ".settings"
        result = self.run_shell('''
cp() { return 1; }
_download .settings settings
''')
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(target.exists())
        self.assertEqual(list(self.home.glob(".settings.tmp.*")), [])

    def test_replace_failure_preserves_destination(self):
        (self.repo / "settings").write_text("new")
        target = self.home / ".settings"
        target.write_text("working")
        result = self.run_shell('''
mv() { return 1; }
_download .settings settings
''')
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(target.read_text(), "working")
        self.assertEqual(list(self.home.glob(".settings.tmp.*")), [])

    def test_directory_destination_is_rejected(self):
        (self.repo / "settings").write_text("new")
        target = self.home / ".settings"
        target.mkdir()
        result = self.run_shell('_download .settings settings\n')
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(list(target.iterdir()), [])

    def test_local_copy_supports_spaces_and_private_files(self):
        (self.repo / "config with spaces").write_text("settings")
        result = self.run_shell('_download ".ssh/config with spaces" "config with spaces"\n')
        self.assertEqual(result.returncode, 0, result.stderr)
        target = self.home / ".ssh/config with spaces"
        self.assertEqual(target.read_text(), "settings")
        self.assertEqual(target.stat().st_mode & 0o777, 0o600)

    def test_pip_marker_advances_only_after_all_updates_succeed(self):
        marker = self.home / ".toast/last_update_pip"
        marker.parent.mkdir()
        for tools_status, package_status in [(0, 7), (7, 0), (0, 0)]:
            with self.subTest(tools_status=tools_status, package_status=package_status):
                marker.unlink(missing_ok=True)
                body = f'''python3() {{
  case "$*" in
    *"pip show"*) return 1 ;;
    *toast-cli*) return {package_status} ;;
    *) return {tools_status} ;;
  esac
}}
sudo() {{ "$@"; }}
'''
                result = self.run_shell(body + self.block("# PIP 패키지 설치 (버전 체크 포함)", "# Step 7:"))
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(marker.exists(), tools_status == package_status == 0)

    def test_pip_package_failure_propagates_after_bounded_fallbacks(self):
        result = self.run_shell('''
python3() {
  printf '%s\\n' "$*" >> "$HOME/pip-calls"
  return 7
}
sudo() { "$@"; }
_install_pip_package toast-cli
''')
        self.assertNotEqual(result.returncode, 0)
        installs = [line for line in (self.home / "pip-calls").read_text().splitlines() if "pip install" in line]
        self.assertEqual(len(installs), 4)

    def test_apt_checks_all_packages_and_reports_installation_failure(self):
        for installed, install_status in [(True, 0), (False, 0), (False, 7)]:
            with self.subTest(installed=installed, install_status=install_status):
                log = self.home / "apt-calls"
                log.unlink(missing_ok=True)
                body = f'''OS_NAME=linux
_should_update() {{ return 1; }}
zsh() {{ :; }}
jq() {{ :; }}
dpkg-query() {{
  printf 'install ok installed\\n'
  return {0 if installed else 1}
}}
sudo() {{ printf '%s\\n' "$*" >> "$HOME/apt-calls"; return {install_status}; }}
'''
                result = self.run_shell(body + self.block("# Linux 설정 (APT 패키지 관리)", "# Homebrew 설치"))
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(log.exists(), not installed)
                if not installed and install_status:
                    self.assertIn("Failed to install essential packages", result.stdout)
                    self.assertNotIn("✓ Essential packages installed", result.stdout)


if __name__ == "__main__":
    unittest.main()
