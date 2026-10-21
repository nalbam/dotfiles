#!/usr/bin/env python3
"""Focused, offline tests for module behavior: packages, throttling, upgrades and the Spark stack."""

import hashlib
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import unittest
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parent))
from dot_testlib import Machine  # noqa: E402

RECORD = 'printf "%s\\n" "$(basename "$0") $*" >> "$CALLS"\n'


class ModuleCase(unittest.TestCase):
    platform = ("Linux", "x86_64")

    def setUp(self):
        self.machine = Machine(self)
        self.machine.uname(*self.platform)
        self.calls = self.machine.root / "calls"
        self.machine.env.update(CALLS=str(self.calls), DOT_SYSROOT=str(self.machine.root / "sysroot"))

    def module(self, name, body, **env):
        """Load module NAME and run BODY; `run FN` executes FN in a subshell and prints rc=N."""
        script = f'''dot_detect || exit 9
dot_module_load {name} || exit 8
run() {{ ( "$@" ); printf 'rc=%s\\n' "$?"; }}
''' + body
        return self.machine.shell(script, **env)

    def recorded(self):
        if not self.calls.exists():
            return []
        lines = self.calls.read_text().splitlines()
        self.calls.write_text("")
        return lines

    def stamp(self, key, value="now"):
        stamps = self.machine.state / "stamps"
        stamps.mkdir(parents=True, exist_ok=True)
        import time
        (stamps / key).write_text(f"{int(time.time()) if value == 'now' else value}\n")


class AptTests(ModuleCase):
    def setUp(self):
        super().setUp()
        self.machine.stub("dpkg-query", '''for p; do :; done
case " $MISSING " in *" $p "*) printf 'install ok unpacked' ;; *) printf '%s' "${STATUS:-install ok installed}" ;; esac
''')
        self.machine.stub("apt-get", RECORD)
        self.machine.stub("sudo", RECORD + 'exit "${SUDO_STATUS:-0}"\n')
        self.machine.stub("apt", RECORD + 'printf "Listing...\\npkg/noble 2 amd64 [upgradable from: 1]\\n"\n')

    def test_installed_packages_need_no_privileges(self):
        for status in ("install ok installed", "hold ok installed"):
            with self.subTest(status=status):
                result = self.module("apt", "run apt::up\n", STATUS=status)
                self.assertIn("rc=0", result.stdout, result.stderr)
                self.assertEqual(self.recorded(), [])

    def test_only_missing_packages_are_installed(self):
        result = self.module("apt", "run apt::up\n", MISSING="zsh jq")
        self.assertIn("rc=0", result.stdout, result.stderr)
        calls = self.recorded()
        self.assertEqual(len(calls), 2)
        self.assertIn("apt-get update -q", calls[0])
        self.assertTrue(calls[1].endswith("apt-get install -y -q jq zsh"), calls)

    def test_install_failure_fails_the_module(self):
        result = self.module("apt", "run apt::up\n", MISSING="zsh", SUDO_STATUS="100")
        self.assertIn("rc=1", result.stdout)
        self.assertIn("APT installation failed", result.stderr)

    def test_system_upgrade_without_yes_changes_nothing(self):
        result = self.module("apt", "run apt::system_upgrade false\n", DOT_PLATFORM="dgx-spark")
        self.assertIn("rc=0", result.stdout, result.stderr)
        self.assertIn("pkg/noble", result.stdout)
        self.assertIn("DGX Spark", result.stdout)
        calls = self.recorded()
        self.assertFalse([call for call in calls if "upgrade" in call.split()[1:3]], calls)


class BrewTests(ModuleCase):
    def setUp(self):
        super().setUp()
        self.machine.stub("brew", RECORD + 'case "$1" in update) exit "${UPDATE_STATUS:-0}" ;; '
                                           'bundle) exit "${BUNDLE_STATUS:-0}" ;; '
                                           'trust) exit "${TRUST_STATUS:-0}" ;; esac\n')
        self.brewfile = self.machine.repo / "packages/Brewfile.linux"
        self.marker = self.machine.state / "applied/Brewfile"

    def brew_calls(self):
        return [call.split()[1] for call in self.recorded()
                if call.startswith("brew ") and call.split()[1] != "trust"]

    def test_third_party_entries_are_trusted_before_bundle(self):
        self.brewfile.write_text('tap "acme/tap"\nbrew "jq"\nbrew "acme/tap/tool"\n'
                                 '  cask "acme/tap/app" # comment\ncask "font-x"\n')
        result = self.module("brew", "run brew::up\n")
        self.assertIn("rc=0", result.stdout, result.stderr)
        calls = [call for call in self.recorded() if call.startswith("brew ")]
        trusts = [call for call in calls if call.split()[1] == "trust"]
        self.assertEqual(trusts, ["brew trust --help",
                                  "brew trust --quiet --formula acme/tap/tool",
                                  "brew trust --quiet --cask acme/tap/app"])
        self.assertLess(calls.index(trusts[-1]), [c.split()[1] for c in calls].index("bundle"))

    def test_homebrew_without_trust_skips_it(self):
        self.brewfile.write_text('brew "acme/tap/tool"\n')
        result = self.module("brew", "run brew::up\n", TRUST_STATUS="1")
        self.assertIn("rc=0", result.stdout, result.stderr)
        calls = [call for call in self.recorded() if call.startswith("brew ")]
        self.assertEqual([call for call in calls if call.split()[1] == "trust"], ["brew trust --help"])
        self.assertIn("bundle", [call.split()[1] for call in calls])
        self.assertNotIn("brew trust failed", result.stdout + result.stderr)

    def test_brewfile_change_bypasses_the_throttle(self):
        self.stamp("brew")
        result = self.module("brew", "run brew::up\n")
        self.assertIn("rc=0", result.stdout, result.stderr)
        self.assertEqual(self.brew_calls(), ["bundle", "cleanup"])
        self.assertEqual(self.marker.read_bytes(), self.brewfile.read_bytes())
        result = self.module("brew", "run brew::up\n")
        self.assertIn("next upgrade after 6 hours", result.stdout)
        self.assertEqual(self.brew_calls(), [])

    def test_due_upgrade_stamps_only_after_full_success(self):
        for update, bundle, stamped in (("1", "0", False), ("0", "1", False), ("0", "0", True)):
            with self.subTest(update=update, bundle=bundle):
                shutil.rmtree(self.machine.state, ignore_errors=True)
                result = self.module("brew", "run brew::up\n", UPDATE_STATUS=update, BUNDLE_STATUS=bundle)
                self.assertIn("rc=0", result.stdout, result.stderr)
                self.assertEqual((self.machine.state / "stamps/brew").exists(), stamped)
                self.assertEqual(self.marker.exists(), bundle == "0")
                self.assertEqual(stamped, "⚠" not in result.stdout)
                self.recorded()

    def test_comparison_failure_never_skips_or_applies(self):
        self.stamp("brew")
        self.marker.parent.mkdir(parents=True)
        self.marker.write_text("previous Brewfile")
        result = self.module("brew", "dot_md5() { return 7; }\nrun brew::up\n")
        self.assertIn("rc=1", result.stdout)
        self.assertIn("Failed to compare the Brewfile", result.stderr)
        self.assertEqual(self.brew_calls(), [])
        self.assertEqual(self.marker.read_text(), "previous Brewfile")

    def test_low_memory_on_dgx_spark_skips_upgrades(self):
        meminfo = self.machine.root / "sysroot/proc/meminfo"
        meminfo.parent.mkdir(parents=True)
        meminfo.write_text("MemAvailable:    4194304 kB\n")
        result = self.module("brew", "run brew::up\n", DOT_PLATFORM="dgx-spark")
        self.assertIn("rc=0", result.stdout, result.stderr)
        self.assertIn("4GiB memory available", result.stdout)
        self.assertEqual(self.brew_calls(), [])
        self.assertFalse((self.machine.state / "stamps/brew").exists())
        result = self.module("brew", "run brew::up\n", DOT_PLATFORM="dgx-spark", DOT_BREW_MIN_MEMORY_GIB="2")
        self.assertIn("bundle", self.brew_calls())


class BrewBootstrapTests(ModuleCase):
    def test_failed_or_partial_install_is_not_reported_as_installed(self):
        for script in ('return 7', 'return 0'):
            with self.subTest(installer=script):
                result = self.module("brew", f"dot_install_script() {{ {script}; }}\nrun brew::up\n")
                self.assertIn("rc=1", result.stdout)
                self.assertNotIn("Homebrew installed", result.stdout)
                self.assertTrue("installation failed" in result.stderr or "not on PATH" in result.stderr,
                                result.stderr)


class GitTests(ModuleCase):
    def test_every_identity_include_is_deployed_and_effective(self):
        result = self.module("git", "run git::up\n")
        self.assertIn("rc=0", result.stdout, result.stderr)
        root = Path(__file__).resolve().parent.parent
        env = dict(self.machine.env, PATH="/usr/bin:/bin", GIT_CONFIG_NOSYSTEM="1")
        for account, profile in [("nalbam", "nalbam"), ("opspresso", "nalbam"), ("yujh404", "yujh404"),
                                 ("nalbam-me", "nalbam-me"), ("nalbam-bot", "nalbam-bot")]:
            with self.subTest(account=account):
                workspace = self.machine.home / "workspace/github.com" / account / "example"
                subprocess.run(["git", "init", "-q", str(workspace)], env=env, check=True)
                for key in ("user.name", "user.email"):
                    actual = subprocess.check_output(["git", "-C", str(workspace), "config", "--get", key], env=env)
                    expected = subprocess.check_output(
                        ["git", "config", "--file", str(root / ("config/git/gitconfig-" + profile)), "--get", key],
                        env=env)
                    self.assertEqual(actual, expected, f"{key} for {profile}")


class NodeTests(ModuleCase):
    def nvm(self, actual="24.21.0", alias_status=0, installed=True):
        home = self.machine.home
        node_bin = home / ".nvm/versions/node/v24.21.0/bin"
        node_bin.mkdir(parents=True)
        (node_bin / "node").write_text(f'#!/bin/sh\nprintf "v{actual}\\n"\n')
        (node_bin / "node").chmod(0o755)
        self.machine.stub("node", 'printf "v26.11.1\\n"\n')
        if installed:
            (home / ".nvm/installed").touch()
        (home / ".nvm/nvm.sh").write_text(f'''nvm() {{
  printf '%s\\n' "$*" >> "$NVM_DIR/calls"
  case "$1" in
    version) if [ -f "$NVM_DIR/installed" ]; then printf 'v24.21.0\\n'; else printf 'N/A\\n'; fi ;;
    install) touch "$NVM_DIR/installed" ;;
    alias) return {alias_status} ;;
    use) export NVM_BIN="$NVM_DIR/versions/node/v24.21.0/bin" ;;
    *) return 99 ;;
  esac
}}
''')
        return home / ".nvm/calls"

    def test_installs_node_24_and_reports_the_real_executable(self):
        calls = self.nvm(installed=False)
        result = self.module("node", "run node::up\n")
        self.assertIn("rc=0", result.stdout, result.stderr)
        self.assertIn("Node.js v24.21.0 is the default", result.stdout)
        lines = calls.read_text().splitlines()
        self.assertEqual(lines[:2], ["version 24", "install 24"])
        self.assertLess(lines.index("alias default 24"), lines.index("use default"))
        self.assertTrue((self.machine.state / "stamps/node").exists())

    def test_alias_failure_fails(self):
        self.nvm(alias_status=7)
        result = self.module("node", "run node::up\n")
        self.assertIn("rc=1", result.stdout)
        self.assertIn("Failed to select Node.js 24", result.stderr)
        self.assertFalse((self.machine.state / "stamps/node").exists())

    def test_wrong_executable_version_fails(self):
        self.nvm(actual="26.11.1")
        result = self.module("node", "run node::up\n")
        self.assertIn("rc=1", result.stdout)
        self.assertIn("v26.11.1", result.stderr)

    def test_installed_and_not_due_is_skipped(self):
        calls = self.nvm()
        self.stamp("node")
        result = self.module("node", "run node::up\n")
        self.assertIn("rc=0", result.stdout, result.stderr)
        self.assertIn("checked", result.stdout)
        self.assertNotIn("install", calls.read_text())


class PythonTests(ModuleCase):
    def test_fallback_chain_and_stamp(self):
        self.machine.stub("python3", RECORD + '''n=$(grep -c "pip install" "$CALLS")
[ "$n" -ge "${SUCCEED_AT:-99}" ]
''')
        self.machine.stub("sudo", '"$@"\n')
        result = self.module("python", "run python::up\n")
        self.assertIn("rc=0", result.stdout, result.stderr)
        installs = [call for call in self.recorded() if "pip install" in call]
        self.assertEqual(len(installs), 4)
        self.assertIn("--break-system-packages --user", installs[2])
        self.assertIn("Failed to install toast-cli", result.stdout)
        self.assertFalse((self.machine.state / "stamps/python").exists())
        result = self.module("python", "run python::up\n", SUCCEED_AT="3")
        self.assertEqual(len([c for c in self.recorded() if "pip install" in c]), 3)
        self.assertTrue((self.machine.state / "stamps/python").exists())

    def test_one_failed_package_prevents_the_stamp(self):
        self.machine.stub("python3", RECORD + 'case "$*" in *broken*) exit 1 ;; esac\n')
        self.machine.stub("sudo", '"$@"\n')
        result = self.module("python", "run python::up\n", DOT_PIP_PACKAGES="toast-cli broken")
        self.assertIn("Failed to install broken", result.stdout)
        self.assertFalse((self.machine.state / "stamps/python").exists())


class ShellTests(ModuleCase):
    def test_incomplete_oh_my_zsh_is_preserved_and_retried(self):
        omz = self.machine.home / ".oh-my-zsh"
        omz.mkdir()
        (omz / "custom").write_text("personal theme")
        body = '''dot_install_script() {
  printf attempt >> "$HOME/attempts"
  mkdir -p "$HOME/.oh-my-zsh" && printf installed > "$HOME/.oh-my-zsh/oh-my-zsh.sh"
}
run _shell_oh_my_zsh
'''
        result = self.module("shell", body)
        self.assertIn("rc=0", result.stdout, result.stderr)
        self.assertIn("Oh My Zsh installed", result.stdout)
        backups = list(self.machine.home.glob(".oh-my-zsh.backup.*/oh-my-zsh/custom"))
        self.assertEqual([b.read_text() for b in backups], ["personal theme"])
        result = self.module("shell", body)
        self.assertEqual((self.machine.home / "attempts").read_text(), "attempt")

    def test_partial_bootstrap_is_not_reported_as_installed(self):
        body = '''dot_install_script() {
  mkdir -p "$HOME/.oh-my-zsh" && printf partial > "$HOME/.oh-my-zsh/oh-my-zsh.sh"
  return 7
}
run _shell_oh_my_zsh
'''
        result = self.module("shell", body)
        self.assertNotIn("Oh My Zsh installed", result.stdout)
        self.assertIn("installation failed", result.stdout)
        self.assertFalse((self.machine.home / ".oh-my-zsh").exists())
        backups = list(self.machine.home.glob(".oh-my-zsh.backup.*/oh-my-zsh/oh-my-zsh.sh"))
        self.assertEqual([b.read_text() for b in backups], ["partial"])


@unittest.skipUnless(shutil.which("unzip"), "unzip is required for the AWS CLI archive")
class ServerTests(ModuleCase):
    def setUp(self):
        super().setUp()
        self.downloads = self.machine.root / "downloads"
        self.downloads.mkdir()
        archive = self.machine.root / "awscli.zip"
        with zipfile.ZipFile(archive, "w") as bundle:
            info = zipfile.ZipInfo("aws/install")
            info.create_system = 3
            info.external_attr = 0o100755 << 16
            bundle.writestr(info, '#!/bin/sh\nprintf "install %s\\n" "$*" >> "$CALLS"\n')
        self.machine.stub("aws", 'printf "%s Python/3\\n" "${AWS_VERSION:-aws-cli/1.0.0}"\n')
        self.machine.stub("curl", RECORD + f'[ "${{CURL_STATUS:-0}}" = 0 ] || exit "$CURL_STATUS"\n'
                                           f'while [ "$1" != -o ]; do shift; done\ncp "{archive}" "$2"\n')
        self.machine.stub("sudo", '"$@"\n')
        self.machine.env["TMPDIR"] = str(self.downloads)

    def test_current_v2_is_not_downloaded_until_due(self):
        self.stamp("server")
        result = self.module("server", "run _server_awscli\n", AWS_VERSION="aws-cli/2.27.0")
        self.assertIn("rc=0", result.stdout, result.stderr)
        self.assertEqual(self.recorded(), [])

    def test_v1_is_replaced_and_temporary_files_removed(self):
        result = self.module("server", "run _server_awscli\n")
        self.assertIn("rc=0", result.stdout, result.stderr)
        calls = self.recorded()
        self.assertIn("awscli-exe-linux-x86_64.zip", calls[0])
        self.assertEqual(calls[1], "install --update")
        self.assertEqual(list(self.downloads.iterdir()), [])

    def test_download_failure_is_reported_and_cleaned(self):
        result = self.module("server", "run _server_awscli\n", CURL_STATUS="22")
        self.assertIn("rc=1", result.stdout)
        self.assertIn("AWS CLI v2 installation failed", result.stdout)
        self.assertEqual(len([c for c in self.recorded() if c.startswith("curl")]), 3)
        self.assertEqual(list(self.downloads.iterdir()), [])

    def test_active_swap_is_left_alone(self):
        self.machine.stub("swapon", RECORD + 'printf "/dev/zram0\\n"\n')
        result = self.module("server", "run _server_swap\n")
        self.assertIn("rc=0", result.stdout)
        self.assertEqual(self.recorded(), ["swapon --show=NAME --noheadings"])


class K3sTests(ModuleCase):
    platform = ("Linux", "aarch64")
    LATEST = {"v1.35": "v1.35.9+k3s1", "v1.36": "v1.36.5+k3s1", "v1.37": "v1.37.2+k3s1",
              "v1.38": "v1.38.1+k3s1", "stable": "v1.38.1+k3s1"}

    def setUp(self):
        super().setUp()
        self.binary = b"new k3s binary"
        self.sums = self.machine.root / "sums"
        pairs = " ".join(f"{channel}={version}" for channel, version in self.LATEST.items())
        self.machine.stub("curl", RECORD + 'case "$*" in\n'
                          '  *redirect_url*)\n'
                          '    for url; do :; done\n'
                          '    channel="${url##*/}"\n'
                          f'    for pair in {pairs}; do\n'
                          '      [ "${pair%%=*}" = "$channel" ] && printf "https://github.com/k3s-io/k3s/releases/tag/%s" "${pair#*=}"\n'
                          '    done ;;\n'
                          f'  *sha256sum*) while [ "$1" != -o ]; do shift; done; cp "{self.sums}" "$2" ;;\n'
                          '  *) while [ "$1" != -o ]; do shift; done; printf "new k3s binary" > "$2" ;;\n'
                          'esac\n')
        self.machine.stub("sha256sum", f'{shlex.quote(sys.executable)} -c "import hashlib, sys; '
                                       'print(hashlib.sha256(open(sys.argv[1], \'rb\').read()).hexdigest(), sys.argv[1])" "$1"\n')
        self.machine.stub("sudo", RECORD)
        self.machine.stub("systemctl", 'case "$1 $2" in "cat k3s-agent.service") exit "${AGENT:-1}" ;; esac\n')

    def installed(self, version):
        binary = self.machine.root / "sysroot/usr/local/bin/k3s"
        binary.parent.mkdir(parents=True, exist_ok=True)
        binary.write_text(f'#!/bin/sh\nprintf "k3s version {version} (abcdef)\\ngo version go1.24\\n"\n')
        binary.chmod(0o755)

    def verified_sums(self, name):
        self.sums.write_text(f"{hashlib.sha256(self.binary).hexdigest()}  {name}\nffff  other\n")

    def downloads(self):
        return [call for call in self.recorded() if "redirect_url" not in call]

    def test_latest_parses_the_channel_redirect(self):
        result = self.module("k3s", "_k3s_latest v1.36\n")
        self.assertEqual(result.stdout.strip(), self.LATEST["v1.36"])

    def test_channel_defaults(self):
        result = self.module("k3s", "_k3s_channel\n")
        self.assertEqual(result.stdout.strip(), "stable", "a new install follows stable")
        self.installed("v1.36.2+k3s1")
        result = self.module("k3s", "_k3s_channel\n")
        self.assertEqual(result.stdout.strip(), "v1.36", "an installed node stays on its minor version")
        result = self.module("k3s", "_k3s_channel\n", DOT_K3S_CHANNEL="v1.37")
        self.assertEqual(result.stdout.strip(), "v1.37")

    def test_checksum_mismatch_keeps_the_binary(self):
        self.sums.write_text("0000 k3s-arm64\n")
        result = self.module("k3s", f"run _k3s_upgrade {self.LATEST['v1.36']}\n")
        self.assertIn("rc=1", result.stdout)
        self.assertIn("checksum mismatch", result.stderr)
        self.assertFalse([call for call in self.recorded() if call.startswith("sudo")])

    def test_release_assets_per_architecture(self):
        for arch, binary, sums in (("aarch64", "k3s-arm64", "sha256sum-arm64.txt"),
                                   ("armv7l", "k3s-armhf", "sha256sum-arm.txt"),
                                   ("x86_64", "k3s", "sha256sum-amd64.txt")):
            with self.subTest(arch=arch):
                self.machine.uname("Linux", arch)
                self.verified_sums(binary)
                result = self.module("k3s", f"run _k3s_upgrade {self.LATEST['v1.36']}\n")
                self.assertIn("rc=0", result.stdout, result.stderr)
                calls = self.recorded()
                self.assertTrue(calls[0].endswith(f"v1.36.5%2Bk3s1/{binary}"), calls[0])
                self.assertTrue(calls[1].endswith(f"v1.36.5%2Bk3s1/{sums}"), calls[1])

    def test_patch_upgrade_replaces_the_agent_binary(self):
        self.installed("v1.36.2+k3s1")
        self.verified_sums("k3s-arm64")
        result = self.module("k3s", "run k3s::up\n", AGENT="0")
        self.assertIn("rc=0", result.stdout, result.stderr)
        self.assertIn("v1.36.2+k3s1 -> v1.36.5+k3s1", result.stdout)
        privileged = [call for call in self.recorded() if call.startswith("sudo")]
        self.assertTrue(privileged[0].startswith("sudo install -m 755 "))
        self.assertEqual(privileged[1], "sudo mv -f /usr/local/bin/k3s.dot-new /usr/local/bin/k3s")
        self.assertEqual(privileged[-1], "sudo systemctl restart k3s-agent")
        self.assertTrue((self.machine.state / "stamps/k3s").exists())

    def test_current_release_is_stamped_without_download(self):
        self.installed(self.LATEST["v1.36"])
        result = self.module("k3s", "run k3s::up\n")
        self.assertIn("rc=0", result.stdout, result.stderr)
        self.assertIn("is the newest release of v1.36", result.stdout)
        self.assertEqual(self.downloads(), [])
        self.assertTrue((self.machine.state / "stamps/k3s").exists())
        result = self.module("k3s", "run k3s::up\n")
        self.assertIn("checked", result.stdout)
        self.assertEqual(self.recorded(), [], "a stamped node makes no request until due")

    def test_minor_upgrade_is_limited_to_one_version(self):
        self.installed("v1.36.5+k3s1")
        self.verified_sums("k3s-arm64")
        result = self.module("k3s", "run k3s::up\n", DOT_K3S_CHANNEL="v1.38")
        self.assertIn("rc=0", result.stdout, result.stderr)
        self.assertIn("skips a minor version; set DOT_K3S_CHANNEL=v1.37", result.stdout)
        self.assertEqual(self.downloads(), [])
        self.assertFalse((self.machine.state / "stamps/k3s").exists())
        result = self.module("k3s", "run k3s::up\n", DOT_K3S_CHANNEL="v1.37")
        self.assertIn("v1.36.5+k3s1 -> v1.37.2+k3s1", result.stdout, result.stderr)
        self.assertIn("sudo systemctl restart k3s", self.recorded())

    def test_older_channel_changes_nothing(self):
        self.installed("v1.36.5+k3s1")
        result = self.module("k3s", "run k3s::up\n", DOT_K3S_CHANNEL="v1.35")
        self.assertIn("rc=0", result.stdout, result.stderr)
        self.assertIn("is newer than channel v1.35", result.stdout)
        self.assertEqual(self.downloads(), [])


class DockerTests(ModuleCase):
    def setUp(self):
        super().setUp()
        self.machine.stub("sudo", RECORD)
        self.machine.stub("apt-get", RECORD)
        self.sysroot = self.machine.root / "sysroot"

    def test_installed_docker_is_never_upgraded_or_regrouped(self):
        self.machine.stub("docker", 'printf "Docker version 28.0.0\\n"\n')
        result = self.module("docker", "run docker::up\n", DOT_PLATFORM="linux")
        self.assertIn("rc=0", result.stdout, result.stderr)
        self.assertIn("upgrades run with dot upgrade-system", result.stdout)
        self.assertEqual(self.recorded(), [])
        self.assertFalse((self.machine.state / "stamps/docker").exists())

    def install(self):
        self.machine.stub("dpkg-query", "exit 1\n")
        body = ('dot_has() { [ "$1" != docker ] && command -v "$1" >/dev/null 2>&1; }\n'
                '_docker_repository() { printf "repository\\n" >> "$CALLS"; }\n'
                'run docker::up\n')
        return self.module("docker", body, DOT_PLATFORM="linux")

    def test_install_adds_the_repository_daemon_config_and_group(self):
        result = self.install()
        self.assertIn("rc=0", result.stdout, result.stderr)
        calls = self.recorded()
        self.assertEqual(calls[0], "repository")
        self.assertTrue(any(call.endswith("apt-get install -y -q docker-ce docker-ce-cli containerd.io "
                                          "docker-buildx-plugin docker-compose-plugin") for call in calls), calls)
        self.assertIn("sudo tee /etc/docker/daemon.json", calls)
        self.assertIn("sudo systemctl restart docker", calls)
        self.assertEqual(calls[-1], "sudo usermod -aG docker dotuser")

    def test_existing_daemon_config_is_kept(self):
        daemon = self.sysroot / "etc/docker/daemon.json"
        daemon.parent.mkdir(parents=True)
        daemon.write_text('{"data-root":"/data/docker"}\n')
        result = self.install()
        self.assertIn("rc=0", result.stdout, result.stderr)
        self.assertNotIn("sudo tee /etc/docker/daemon.json", self.recorded())


class StatusTests(ModuleCase):
    def test_absent_tools_are_reported(self):
        for name in ("claude", "nvim", "server", "python", "brew"):
            with self.subTest(module=name):
                result = self.module(name, f"{name}::status\n")
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn("not installed", result.stdout)


class ShellLoginTests(ModuleCase):
    def oh_my_zsh(self, git_status):
        for path in (".oh-my-zsh/.git", ".dracula/zsh/.git", ".oh-my-zsh/themes"):
            (self.machine.home / path).mkdir(parents=True, exist_ok=True)
        (self.machine.home / ".oh-my-zsh/oh-my-zsh.sh").write_text("# installed\n")
        theme = self.machine.home / ".oh-my-zsh/themes/dracula.zsh-theme"
        if not theme.is_symlink():
            theme.symlink_to(self.machine.home / ".dracula/zsh/dracula.zsh-theme")
        self.machine.stub("git", RECORD + f"exit {git_status}\n")

    def test_stamp_only_after_successful_updates(self):
        for status, stamped in ((1, False), (0, True)):
            with self.subTest(git_status=status):
                shutil.rmtree(self.machine.state, ignore_errors=True)
                self.oh_my_zsh(status)
                result = self.module("shell", "run shell::up\n", SHELL="/bin/zsh")
                self.assertIn("rc=0", result.stdout, result.stderr)
                self.assertEqual((self.machine.state / "stamps/shell").exists(), stamped)
                self.assertEqual("Oh My Zsh update failed" in result.stdout, not stamped)
                self.recorded()

    def test_login_shell_prefers_the_system_zsh(self):
        system = next((path for path in ("/bin/zsh", "/usr/bin/zsh") if Path(path).exists()), None)
        if not system:
            self.skipTest("no system zsh on this host")
        self.machine.stub("zsh", "exit 0\n")
        self.machine.stub("sudo", RECORD)
        self.machine.stub("chsh", RECORD + "exit 1\n")
        result = self.module("shell", "run _shell_login_zsh\n", SHELL="/bin/bash")
        self.assertIn("rc=0", result.stdout, result.stderr)
        calls = self.recorded()
        # On Linux the login shell changes through sudo, never to the Homebrew zsh.
        self.assertIn(f"sudo chsh -s {system} dotuser", calls)
        self.assertFalse([call for call in calls if call.startswith("chsh")], calls)
        self.assertFalse([call for call in calls if str(self.machine.bin / "zsh") in call], calls)

    def test_theme_clones_wait_until_git_is_usable(self):
        if not Path("/usr/bin/git").exists():
            self.skipTest("/usr/bin/git is absent")
        self.machine.uname("Darwin", "arm64")
        self.machine.stub("xcode-select", "exit 2\n")
        for module, function, message in (("shell", "_shell_dracula", "Dracula theme is installed on the next run"),
                                          ("terminal", "terminal::up", "iTerm2 colors are installed on the next run")):
            with self.subTest(module=module):
                result = self.module(module, f"run {function}\n", DOT_PLATFORM="macos")
                self.assertIn("rc=0", result.stdout, result.stderr)
                self.assertIn(message, result.stdout)
                self.assertFalse((self.machine.home / ".dracula").exists())


class SparkTests(ModuleCase):
    platform = ("Linux", "aarch64")
    GRAFANA = {"GCLOUD_RW_API_KEY": "token", "GCLOUD_FM_COLLECTOR_ID": "spark", "GCLOUD_FM_URL": "https://fm.example",
               "GCLOUD_FM_USERNAME": "1", "GCLOUD_PROM_URL": "https://prom.example", "GCLOUD_PROM_USERNAME": "2"}

    def setUp(self):
        super().setUp()
        self.source = self.machine.repo / "stacks/dgx-spark"
        self.runtime = self.machine.root / "dgx-spark"
        scripts = self.source / "scripts"
        for name in ("deploy.sh", "health-check.sh", "setup-grafana.sh", "setup-vibemon.sh"):
            variable = "FAIL_" + name.split(".")[0].replace("-", "_").upper()
            (scripts / name).write_text("#!/bin/sh\n" + RECORD + f'exit "${{{variable}:-0}}"\n')
            (scripts / name).chmod(0o755)
        (self.source / "grafana/model-targets.json").write_text("source must not be copied\n")
        self.machine.stub("systemctl", 'exit "${ACTIVE:-1}"\n')
        self.machine.env.update(DOT_PLATFORM="dgx-spark", DOT_SPARK_DIR=str(self.runtime))

    def install_runtime(self):
        shutil.copytree(self.source, self.runtime, ignore=shutil.ignore_patterns("model-targets.json", "bench"))
        runtime_only = {".env": "SPARK_MODE=flash\n", ".env.grafana": "GCLOUD_RW_API_KEY=x\n",
                        "backups/old.env": "backup\n", "grafana/model-targets.json": "generated\n"}
        for name, content in runtime_only.items():
            (self.runtime / name).parent.mkdir(parents=True, exist_ok=True)
            (self.runtime / name).write_text(content)
        return runtime_only

    def change(self, name, text="changed\n"):
        (self.source / name).write_text(text)

    def scripts_called(self):
        return [call.split()[0] for call in self.recorded()]

    def results(self, result):
        return [line for line in result.stdout.splitlines() if line.startswith("rc=")]

    def test_llm_adopts_a_matching_runtime_without_deploying(self):
        self.install_runtime()
        result = self.module("llm", "run llm::up\n")
        self.assertIn("rc=0", result.stdout, result.stderr)
        self.assertIn("Adopted the running stack", result.stdout)
        self.assertEqual(self.scripts_called(), [])
        self.assertTrue((self.machine.state / "applied/spark-llm").exists())
        # Documentation is not part of the stack.
        self.change("README.md", "# edited\n")
        result = self.module("llm", "run llm::up\n")
        self.assertIn("Stack matches the repository (mode: flash)", result.stdout)

    def test_changed_stack_on_a_deployed_host_is_reported_not_deployed(self):
        self.install_runtime()
        self.module("llm", "run llm::up\n")
        self.change("Caddyfile.api")
        for env in ({}, {"DOT_FORCE": "true"}):
            with self.subTest(env=env):
                result = self.module("llm", "run llm::up\n", **env)
                self.assertIn("rc=0", result.stdout, result.stderr)
                self.assertIn("⚠", result.stdout)
                self.assertIn("dot llm deploy", result.stdout)
                self.assertEqual(self.scripts_called(), [])
                self.assertNotEqual((self.runtime / "Caddyfile.api").read_text(), "changed\n",
                                    "nothing is copied before the operator deploys")

    def test_adding_deploys_changes_and_keeps_runtime_files(self):
        runtime_only = self.install_runtime()
        self.change("docker-compose.yml", (self.source / "docker-compose.yml").read_text() + "# new\n")
        result = self.module("llm", "run llm::up\n", DOT_ADDING="true")
        self.assertIn("rc=0", result.stdout, result.stderr)
        self.assertEqual(self.scripts_called(), ["deploy.sh", "health-check.sh"])
        self.assertTrue((self.runtime / "docker-compose.yml").read_text().endswith("# new\n"))
        for name, content in runtime_only.items():
            self.assertEqual((self.runtime / name).read_text(), content, name)
        self.assertTrue((self.machine.state / "applied/spark-llm").exists())

    def test_failed_deploy_is_not_marked_or_adopted_later(self):
        self.install_runtime()
        self.change("Caddyfile.api")
        for variable in ("FAIL_DEPLOY", "FAIL_HEALTH_CHECK"):
            with self.subTest(failure=variable):
                result = self.module("llm", "run llm::up\n", DOT_ADDING="true", **{variable: "1"})
                self.assertIn("rc=1", result.stdout)
                self.assertIn("Deployment failed", result.stderr)
                self.assertFalse((self.machine.state / "applied/spark-llm").exists())
                self.recorded()
        # The runtime now matches the repository, but dot wrote it: no adoption.
        result = self.module("llm", "run llm::up\n")
        self.assertNotIn("Adopted", result.stdout)
        self.assertIn("dot llm deploy", result.stdout)
        self.assertFalse((self.machine.state / "applied/spark-llm").exists())

    def test_first_llm_install_deploys(self):
        result = self.module("llm", "run llm::up\n")
        self.assertIn("rc=0", result.stdout, result.stderr)
        self.assertEqual(self.scripts_called(), ["deploy.sh", "health-check.sh"])
        self.assertFalse((self.runtime / "grafana/model-targets.json").exists())
        self.assertFalse((self.runtime / "bench").exists())
        self.assertFalse(list(self.runtime.rglob("*.md")), "documentation is not copied")

    def test_cli_deploy_marks_only_a_full_deploy(self):
        self.install_runtime()
        compose = "#!/bin/sh\n" + RECORD + '[ "$1" != has-service ] || [ "$2" = llm ]\n'
        for root in (self.source, self.runtime):
            (root / "scripts/compose.sh").write_text(compose)
            (root / "scripts/compose.sh").chmod(0o755)
        result = self.module("llm", "run llm::cli deploy llm\n")
        self.assertIn("rc=0", result.stdout, result.stderr)
        self.assertFalse((self.machine.state / "applied/spark-llm").exists())
        self.recorded()
        result = self.module("llm", "run llm::cli deploy\n")
        self.assertIn("rc=0", result.stdout, result.stderr)
        self.assertTrue((self.machine.state / "applied/spark-llm").exists())

    def test_help_shows_the_runtime_directory(self):
        result = self.module("llm", "llm::cli help\n")
        self.assertIn("Usage: dot llm", result.stdout)
        self.assertIn(f"Runtime directory: {self.runtime}", result.stdout)

    def test_grafana_missing_keys(self):
        self.runtime.mkdir()
        (self.runtime / ".env.grafana").write_text('GCLOUD_RW_API_KEY="token"\nGCLOUD_FM_COLLECTOR_ID=""\n'
                                                   'GCLOUD_FM_URL=https://fm.example\n')
        result = self.module("monitoring", "spark_grafana_missing\n", GCLOUD_PROM_URL="https://prom.example")
        self.assertEqual(result.stdout.split(),
                         ["GCLOUD_FM_COLLECTOR_ID", "GCLOUD_FM_USERNAME", "GCLOUD_PROM_USERNAME"])

    def test_monitoring_needs_the_model_stack(self):
        result = self.module("monitoring", "run monitoring::up\n")
        self.assertIn("rc=1", result.stdout)
        self.assertIn("dot add llm", result.stderr)
        self.assertEqual(self.scripts_called(), [])

    def test_monitoring_adopts_a_matching_setup(self):
        self.install_runtime()
        result = self.module("monitoring", "run monitoring::up\n")
        self.assertIn("Adopted the existing monitoring setup", result.stdout, result.stderr)
        self.assertEqual(self.scripts_called(), [])
        result = self.module("monitoring", "run monitoring::up\n")
        self.assertIn("Monitoring matches the repository", result.stdout)
        result = self.module("monitoring", "run monitoring::up\n", DOT_ADDING="true", **self.GRAFANA)
        self.assertEqual(self.scripts_called(), ["setup-grafana.sh"], result.stderr)

    def test_missing_values_stop_before_any_file_changes(self):
        self.install_runtime()
        self.module("llm", "run llm::up\n")
        self.change("grafana/config.alloy", "new collector config\n")
        before = (self.runtime / "grafana/config.alloy").read_text()
        result = self.module("monitoring", "run monitoring::up\n")
        self.assertIn("rc=1", result.stdout)
        self.assertIn("Grafana Cloud values are missing", result.stderr)
        self.assertIn("dot add monitoring", result.stderr)
        self.assertEqual((self.runtime / "grafana/config.alloy").read_text(), before)
        self.assertEqual(self.scripts_called(), [])

    def test_monitoring_copies_only_its_files(self):
        self.install_runtime()
        self.module("llm", "run llm::up\n")
        self.change("grafana/config.alloy", "new collector config\n")
        self.change("Caddyfile.api")
        result = self.module("monitoring", "run monitoring::up\n", **self.GRAFANA)
        self.assertIn("rc=0", result.stdout, result.stderr)
        self.assertEqual(self.scripts_called(), ["setup-grafana.sh"])
        self.assertEqual((self.runtime / "grafana/config.alloy").read_text(), "new collector config\n")
        self.assertNotEqual((self.runtime / "Caddyfile.api").read_text(), "changed\n")

    def test_vibemon_adopts_an_active_collector_or_sets_it_up(self):
        self.install_runtime()
        result = self.module("vibemon", "run vibemon::up\n", ACTIVE="0")
        self.assertIn("Adopted the active collector", result.stdout, result.stderr)
        self.assertEqual(self.scripts_called(), [])
        result = self.module("vibemon", "run vibemon::up\n", ACTIVE="0", DOT_FORCE="true")
        self.assertIn("Collector is active and matches", result.stdout)
        result = self.module("vibemon", "run vibemon::up\n", ACTIVE="0", DOT_ADDING="true")
        self.assertEqual(self.scripts_called(), ["setup-vibemon.sh"], result.stderr)
        shutil.rmtree(self.machine.state)
        result = self.module("vibemon", "run vibemon::up\n", ACTIVE="1")
        self.assertIn("rc=0", result.stdout, result.stderr)
        self.assertEqual(self.scripts_called(), ["setup-vibemon.sh"])
        result = self.module("vibemon", "run vibemon::up\n", ACTIVE="1", FAIL_SETUP_VIBEMON="1")
        self.assertIn("rc=1", result.stdout)

    def test_vibemon_copies_only_its_files(self):
        self.install_runtime()
        self.module("llm", "run llm::up\n")
        self.change("vibemon.env", "VIBEMON_URL=https://vibemon.io\n")
        self.change("Caddyfile.api")
        result = self.module("vibemon", "run vibemon::up\n", ACTIVE="1")
        self.assertIn("rc=0", result.stdout, result.stderr)
        self.assertEqual((self.runtime / "vibemon.env").read_text(), "VIBEMON_URL=https://vibemon.io\n")
        self.assertNotEqual((self.runtime / "Caddyfile.api").read_text(), "changed\n")

    def test_cli_validates_service_names(self):
        self.install_runtime()
        (self.runtime / "scripts/compose.sh").write_text("#!/bin/sh\n" + RECORD + '[ "$1" != has-service ] || [ "$2" = llm ]\n')
        (self.runtime / "scripts/compose.sh").chmod(0o755)
        result = self.module("llm", "run llm::cli restart 'bad;name'\nrun llm::cli restart nope\nrun llm::cli restart llm\n")
        self.assertEqual(self.results(result), ["rc=2", "rc=2", "rc=0"], result.stderr)
        self.assertIn("compose.sh service restart llm", self.recorded())


if __name__ == "__main__":
    unittest.main()
