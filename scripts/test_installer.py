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
        for key in ("NVM_DIR", "NVM_BIN", "NVM_INC", "BREWPATH"):
            self.env.pop(key, None)
        self.env = {key: value for key, value in self.env.items() if not key.startswith("BASH_FUNC_")}

    def run_shell(self, body):
        return subprocess.run(["/bin/bash", "-c", self.declarations + body],
                              env=self.env, capture_output=True, text=True, timeout=5)

    def block(self, start, end):
        execution = self.source[self.source.index("# 실행 영역"):]
        return execution[execution.index(start):execution.index(end)]

    def nvm_fixture(self, actual_version="24.21.0", alias_status=0, installed=True):
        (self.repo / "shell").mkdir()
        shutil.copy(ROOT / "shell/nvm.sh", self.repo / "shell/nvm.sh")
        node_bin = self.home / ".nvm/versions/node/v24.21.0/bin"
        node_bin.mkdir(parents=True)
        (node_bin / "node").write_text(f'#!/bin/sh\nprintf "v{actual_version}\\n"\n')
        (node_bin / "node").chmod(0o755)
        system_bin = self.home / "system/bin"
        system_bin.mkdir(parents=True)
        (system_bin / "node").write_text('#!/bin/sh\nprintf "v26.11.1\\n"\n')
        (system_bin / "node").chmod(0o755)
        self.env["PATH"] = str(system_bin) + ":" + str(node_bin) + ":/usr/bin:/bin"
        if installed:
            (self.home / ".nvm/installed").touch()
        (self.home / ".nvm/nvm.sh").write_text('''nvm() {
  printf '%s\\n' "$*" >> "$NVM_DIR/calls"
  case "$1" in
    version) if [ -f "$NVM_DIR/installed" ]; then printf 'v24.21.0\\n'; else printf 'N/A\\n'; fi ;;
    install) touch "$NVM_DIR/installed" ;;
    alias) return ''' + str(alias_status) + ''' ;;
    use) export NVM_BIN="$NVM_DIR/versions/node/v24.21.0/bin" ;;
    *) return 99 ;;
  esac
}
''')
        return node_bin

    def test_nvm_bootstrap_reports_the_actual_node_24_and_deploys_shared_startup(self):
        node_bin = self.nvm_fixture(installed=False)
        result = self.run_shell(self.block("# nvm 부트스트랩", "# Claude Code 업데이트") + '\nnode --version; command -v node\n')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Node.js v24.21.0 configured as default", result.stdout)
        self.assertEqual(result.stdout.splitlines()[-2:], ["v24.21.0", str(node_bin / "node")])
        self.assertEqual((self.home / ".config/dotfiles/nvm.sh").read_text(), (ROOT / "shell/nvm.sh").read_text())
        self.assertEqual((self.home / ".nvm/calls").read_text().splitlines(),
                         ["version 24", "install 24", "version 24", "alias default 24", "use default"])

    def test_nvm_success_does_not_hide_a_wrong_executable_version(self):
        self.nvm_fixture(actual_version="26.11.1")
        result = self.run_shell(self.block("# nvm 부트스트랩", "# Claude Code 업데이트") + '\nprintf "warnings=%s\\n" "$WARN_COUNT"\n')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn("configured as default", result.stdout)
        self.assertIn("Node.js 24 was selected, but node resolves to", result.stdout)
        self.assertIn("v26.11.1", result.stdout)
        self.assertIn("warnings=1", result.stdout)

    def test_nvm_alias_failure_stays_visible(self):
        self.nvm_fixture(alias_status=7)
        result = self.run_shell(self.block("# nvm 부트스트랩", "# Claude Code 업데이트"))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Failed to configure Node.js 24 as default", result.stdout)
        self.assertNotIn("configured as default", result.stdout)
        self.assertNotIn("use default", (self.home / ".nvm/calls").read_text())

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

    def test_retry_preserves_diagnostics_and_stops_after_three_attempts(self):
        result = self.run_shell('''
sleep() { printf '%s\\n' "$1" >> "$HOME/waits"; }
operation() { printf 'network failure\\n' >&2; return 7; }
_retry "Operation" operation
''')
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(result.stderr.splitlines(), ["network failure"] * 3)
        self.assertEqual((self.home / "waits").read_text().splitlines(), ["5", "10"])

    def test_unknown_option_stops_before_installation(self):
        result = self.run_shell('set -- --vbie\n' + self.block(
            "# Parse arguments", 'if [ "$VIBE_ONLY" = true ]; then') + '\nprintf "WOULD_INSTALL\\n"\n')
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertIn("Unknown option: --vbie", result.stderr)
        self.assertNotIn("WOULD_INSTALL", result.stdout)
        self.assertEqual(list(self.home.iterdir()), [self.repo])

    def test_help_exits_without_changing_home(self):
        for option in ("-h", "--help"):
            with self.subTest(option=option):
                result = subprocess.run(["/bin/bash", str(ROOT / "run.sh"), option],
                                        env=self.env, capture_output=True, text=True, timeout=5)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn("Usage: bash run.sh", result.stdout)
                self.assertNotIn("INSTALLER", result.stdout)
                self.assertEqual(list(self.home.iterdir()), [self.repo])

    def test_retry_stops_at_first_success(self):
        result = self.run_shell('''
attempt=0
operation() { attempt=$((attempt + 1)); [ "$attempt" -eq 2 ]; }
_retry "Operation" operation || exit 1
printf 'attempts=%s\\n' "$attempt"
''')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("attempts=2", result.stdout)

    def test_bootstrap_download_failure_never_executes_partial_script(self):
        for start, end in (("# Homebrew 설치", "# 신규 macOS 대응"),
                           ("# Oh My ZSH 설치", "# 기본 셸을 ZSH로 변경")):
            with self.subTest(installer=start):
                (self.home / "partial-executed").unlink(missing_ok=True)
                block = self.block(start, end)
                for prefix in ("/opt/homebrew", "/home/linuxbrew/.linuxbrew", "/usr/local"):
                    block = block.replace(prefix, str(self.home / "absent-brew"))
                result = self.run_shell('''
command() {
  if [ "$1" = -v ] && [ "$2" = brew ]; then return 1; fi
  builtin command "$@"
}
curl() {
  local output=""
  while [ "$#" -gt 0 ]; do
    if [ "$1" = -o ]; then output="$2"; shift; fi
    shift
  done
  if [ -n "$output" ]; then
    printf 'touch "$HOME/partial-executed"\\n' > "$output"
  else
    printf 'touch "$HOME/partial-executed"\\n'
  fi
  return 22
}
''' + block)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertFalse((self.home / "partial-executed").exists())
                self.assertIn("install failed", result.stdout)

    def test_remote_script_requires_valid_syntax_and_cleans_staging(self):
        staging = self.home / "staging"
        staging.mkdir()
        self.env["TMPDIR"] = str(staging)
        for payload, succeeds in (("touch \\\"$HOME/bootstrap-ran\\\"", True),
                                  ("touch \\\"$HOME/bootstrap-ran\\\"; if", False)):
            with self.subTest(payload=payload):
                marker = self.home / "bootstrap-ran"
                marker.unlink(missing_ok=True)
                result = self.run_shell('''
curl() {
  while [ "$1" != -o ]; do shift; done
  printf '%s\\n' "''' + payload + '''" > "$2"
}
_install_script https://example.invalid/install.sh
''')
                self.assertEqual(result.returncode == 0, succeeds, result.stderr)
                self.assertEqual(marker.exists(), succeeds)
                self.assertEqual(list(staging.iterdir()), [])

    def test_partial_bootstrap_failure_is_not_reported_as_installed(self):
        for start, end, setup, success in (
                ("# Homebrew 설치", "# 신규 macOS 대응", '''
command() {
  if [ "$1" = -v ] && [ "$2" = brew ]; then [ -f "$HOME/brew-ready" ]; return; fi
  builtin command "$@"
}
_install_script() { touch "$HOME/brew-ready"; return 7; }
''', "✓ Homebrew installed"),
                ("# Oh My ZSH 설치", "# 기본 셸을 ZSH로 변경", '''
_install_script() {
  mkdir -p "$HOME/.oh-my-zsh"
  printf partial > "$HOME/.oh-my-zsh/oh-my-zsh.sh"
  return 7
}
''', "✓ Oh My ZSH installed")):
            with self.subTest(installer=start):
                block = self.block(start, end)
                for prefix in ("/opt/homebrew", "/home/linuxbrew/.linuxbrew", "/usr/local"):
                    block = block.replace(prefix, str(self.home / "absent-brew"))
                result = self.run_shell(setup + block)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertNotIn(success, result.stdout)
                self.assertIn("install failed", result.stdout)
                if "ZSH" in start:
                    self.assertFalse((self.home / ".oh-my-zsh").exists())
                    backups = list(self.home.glob(".oh-my-zsh.backup.*/oh-my-zsh/oh-my-zsh.sh"))
                    self.assertEqual(len(backups), 1)
                    self.assertEqual(backups[0].read_text(), "partial")

    def test_remote_script_preserves_environment_arguments_and_failure_status(self):
        staging = self.home / "staging"
        staging.mkdir()
        self.env["TMPDIR"] = str(staging)
        result = self.run_shell('''
curl() {
  while [ "$1" != -o ]; do shift; done
  cat > "$2" <<'SCRIPT'
printf '<%s>\\n' "$RUNZSH" "$CHSH" "$@" > "$HOME/bootstrap-arguments"
exit 17
SCRIPT
}
RUNZSH=no CHSH=no _install_script https://example.invalid/install.sh 'one two' '' '*'
''')
        self.assertEqual(result.returncode, 17, result.stderr)
        self.assertEqual((self.home / "bootstrap-arguments").read_text().splitlines(),
                         ["<no>", "<no>", "<one two>", "<>", "<*>"])
        self.assertEqual(list(staging.iterdir()), [])

    def test_incomplete_oh_my_zsh_is_preserved_before_a_successful_retry(self):
        incomplete = self.home / ".oh-my-zsh"
        incomplete.mkdir()
        (incomplete / "custom").write_text("personal theme")
        body = '''
_install_script() {
  printf attempt >> "$HOME/omz-attempts"
  mkdir -p "$HOME/.oh-my-zsh"
  printf installed > "$HOME/.oh-my-zsh/oh-my-zsh.sh"
}
''' + self.block("# Oh My ZSH 설치", "# 기본 셸을 ZSH로 변경")
        first = self.run_shell(body)
        self.assertEqual(first.returncode, 0, first.stderr)
        self.assertIn("✓ Oh My ZSH installed", first.stdout)
        backups = list(self.home.glob(".oh-my-zsh.backup.*/oh-my-zsh/custom"))
        self.assertEqual(len(backups), 1)
        self.assertEqual(backups[0].read_text(), "personal theme")
        self.assertEqual((incomplete / "oh-my-zsh.sh").read_text(), "installed")
        second = self.run_shell(body)
        self.assertEqual(second.returncode, 0, second.stderr)
        self.assertEqual((self.home / "omz-attempts").read_text(), "attempt")
        self.assertIn("Oh My ZSH already installed", second.stdout)

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

    def test_checksum_backend_failure_propagates_on_both_platforms(self):
        for platform in ("darwin", "linux"):
            with self.subTest(platform=platform):
                result = self.run_shell(f'OS_NAME={platform}\nmd5() {{ return 7; }}\nmd5sum() {{ return 7; }}\n_md5 absent\n')
                self.assertEqual(result.returncode, 7)

    def test_checksum_failure_preserves_destination_and_backup(self):
        target = self.home / ".settings"
        target.write_text("working")
        backup = self.home / ".settings.backup"
        backup.write_text("previous backup")
        for local_source in (True, False):
            with self.subTest(local_source=local_source):
                source = self.repo / "settings"
                if local_source:
                    source.write_text("new")
                else:
                    source.unlink()
                result = self.run_shell('''
_md5() { return 7; }
curl() {
  while [ "$1" != -o ]; do shift; done
  printf new > "$2"
}
_download .settings settings
''')
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(target.read_text(), "working")
                self.assertEqual(backup.read_text(), "previous backup")
                self.assertEqual(list(self.home.glob(".settings*.tmp.*")), [])

    def test_brewfile_comparison_failure_does_not_skip_or_apply_packages(self):
        (self.home / ".Brewfile").write_text("previous Brewfile")
        for platform in ("darwin", "linux"):
            with self.subTest(platform=platform):
                source = self.repo / platform / "Brewfile"
                source.parent.mkdir()
                source.write_text("new Brewfile")
                body = f'OS_NAME={platform}\n' + '''
_md5() { return 7; }
_should_update() { return 1; }
brew() { printf called >> "$HOME/brew-calls"; }
''' + self.block("# Homebrew 패키지 업데이트", "# nvm 부트스트랩")
                result = self.run_shell(body)
                self.assertNotEqual(result.returncode, 0)
                self.assertFalse((self.home / "brew-calls").exists())
                self.assertEqual((self.home / ".Brewfile").read_text(), "previous Brewfile")

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

    def test_non_regular_backup_is_preserved_and_blocks_replacement(self):
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
                result = self.run_shell('_download .settings settings\n')
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(target.read_text(), "working")
                self.assertEqual(victim.read_text(), "unrelated data")
                if kind == "directory":
                    self.assertEqual(backup.stat().st_mode & 0o777, 0o755)
                    self.assertEqual(list(backup.iterdir()), [])
                    backup.rmdir()
                else:
                    self.assertTrue(backup.is_symlink())
                self.assertEqual(list(self.home.glob(".settings.tmp.*")), [])

    def test_backup_copy_failure_preserves_both_existing_versions(self):
        (self.repo / "settings").write_text("new")
        target = self.home / ".settings"
        target.write_text("working")
        backup = self.home / ".settings.backup"
        backup.write_text("earlier backup")
        result = self.run_shell('''
cp() {
  case "$2" in
    "$HOME/.settings.backup"*) printf partial > "$2"; return 7 ;;
  esac
  command cp "$@"
}
_download .settings settings
''')
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(target.read_text(), "working")
        self.assertEqual(backup.read_text(), "earlier backup")
        self.assertEqual(list(self.home.glob(".settings*.tmp.*")), [])

    def test_backup_replacement_does_not_modify_other_hardlinks(self):
        (self.repo / "settings").write_text("new")
        target = self.home / ".settings"
        target.write_text("working")
        other = self.home / "other"
        other.write_text("unrelated data")
        backup = self.home / ".settings.backup"
        os.link(other, backup)
        result = self.run_shell('_download .settings settings\n')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(target.read_text(), "new")
        self.assertEqual(backup.read_text(), "working")
        self.assertEqual(backup.stat().st_mode & 0o777, 0o600)
        self.assertEqual(other.read_text(), "unrelated data")

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
        for installed, install_status, package_status in [
                (True, 0, "install ok installed"), (True, 0, "hold ok installed"),
                (False, 0, "install ok installed"), (False, 7, "install ok installed")]:
            with self.subTest(installed=installed, install_status=install_status, package_status=package_status):
                log = self.home / "apt-calls"
                log.unlink(missing_ok=True)
                body = f'''OS_NAME=linux
_should_update() {{ return 1; }}
zsh() {{ :; }}
jq() {{ :; }}
dpkg-query() {{
  printf '{package_status}\\n'
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
