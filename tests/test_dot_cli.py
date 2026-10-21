#!/usr/bin/env python3
"""Offline tests for bin/dot: detection, commands, module state, locking and remote execution."""

import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from dot_testlib import Machine  # noqa: E402


class DetectionTests(unittest.TestCase):
    def setUp(self):
        self.machine = Machine(self, copy=False)
        self.sysroot = self.machine.root / "sysroot"

    def put(self, path, content):
        target = self.sysroot / path.lstrip("/")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content)

    def detect(self, system="Linux", machine="x86_64", **env):
        self.machine.uname(system, machine)
        result = subprocess.run(
            ["/bin/bash", "-c", '. "$ROOT/lib/core.sh"; . "$ROOT/lib/detect.sh"; dot_detect_platform'],
            env=dict(self.machine.env, ROOT=str(Path(__file__).resolve().parent.parent),
                     DOT_SYSROOT=str(self.sysroot), **env),
            capture_output=True, text=True, timeout=5)
        self.assertEqual(result.returncode, 0, result.stderr)
        return result.stdout.strip()

    def test_platforms(self):
        self.assertEqual(self.detect("Darwin", "arm64"), "macos")
        self.assertEqual(self.detect(), "linux")
        self.assertEqual(self.detect("FreeBSD"), "unsupported")
        self.assertEqual(self.detect(WSL_DISTRO_NAME="Ubuntu"), "wsl")

    def test_wsl_from_kernel_release(self):
        self.put("/proc/sys/kernel/osrelease", "5.15.153.1-microsoft-standard-WSL2\n")
        self.assertEqual(self.detect(), "wsl")

    def test_dgx_spark_from_release_file_or_dmi(self):
        self.put("/etc/dgx-release", 'DGX_NAME="DGX Spark"\n')
        self.assertEqual(self.detect(machine="aarch64"), "dgx-spark")
        shutil.rmtree(self.sysroot)
        self.put("/sys/devices/virtual/dmi/id/product_name", "NVIDIA_DGX_Spark\n")
        self.assertEqual(self.detect(machine="aarch64"), "dgx-spark")

    def test_ec2_signals(self):
        for path, content in (("/sys/devices/virtual/dmi/id/sys_vendor", "Amazon EC2\n"),
                              ("/sys/devices/virtual/dmi/id/board_asset_tag", "i-0123456789abcdef0\n"),
                              ("/sys/hypervisor/uuid", "ec2e1916-9099-7caf-fd21-012345abcdef\n")):
            with self.subTest(path=path):
                shutil.rmtree(self.sysroot, ignore_errors=True)
                self.put(path, content)
                self.assertEqual(self.detect(), "ec2")
        shutil.rmtree(self.sysroot)
        self.put("/sys/devices/virtual/dmi/id/board_asset_tag", "NONE\n")
        self.assertEqual(self.detect(), "linux")

    def test_raspberry_pi(self):
        self.put("/proc/device-tree/model", "Raspberry Pi 4 Model B Rev 1.4\0")
        self.assertEqual(self.detect(machine="armv7l"), "rpi")


class CommandTests(unittest.TestCase):
    def setUp(self):
        self.machine = Machine(self)
        self.machine.uname("Darwin", "arm64")

    def home_entries(self):
        return sorted(path.name for path in self.machine.home.iterdir())

    def test_help_and_invalid_input_do_not_change_home(self):
        before = self.home_entries()
        result = self.machine.dot("help")
        self.assertEqual(result.returncode, 0)
        self.assertIn("Usage: dot", result.stdout)
        for args in (("bogus",), ("up", "--bogus"), ("run",), ("add", "bogus"), ("platform", "set", "solaris"),
                     ("remove", "bogus")):
            with self.subTest(args=args):
                result = self.machine.dot(*args)
                self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertEqual(self.home_entries(), before)

    def test_unsupported_platform_exits_2(self):
        result = self.machine.dot("list", DOT_PLATFORM="solaris")
        self.assertEqual(result.returncode, 2)
        self.assertIn("Unsupported platform", result.stderr)

    def test_platform_override(self):
        self.assertEqual(self.machine.dot("platform").stdout.strip(), "macos")
        self.assertEqual(self.machine.dot("platform", "set", "ec2").returncode, 0)
        self.assertEqual((self.machine.config / "platform").read_text(), "ec2\n")
        self.assertEqual(self.machine.dot("platform").stdout.strip(), "ec2 (override; detected: macos)")
        self.assertEqual(self.machine.dot("platform", DOT_PLATFORM="rpi").stdout.strip(),
                         "rpi (environment; detected: macos)")
        self.assertEqual(self.machine.dot("platform", "reset").returncode, 0)
        self.assertFalse((self.machine.config / "platform").exists())

    def states(self, **env):
        result = self.machine.dot("list", **env)
        self.assertEqual(result.returncode, 0, result.stderr)
        return {line.split()[0]: line.split()[1] for line in result.stdout.splitlines()[1:]}

    def test_list_states(self):
        states = self.states()
        self.assertEqual(states["brew"], "profile")
        self.assertEqual(states["nvim"], "available")
        self.assertEqual(states["llm"], "unsupported")
        self.machine.config.mkdir(parents=True)
        (self.machine.config / "modules").write_text("nvim\n-brew\n")
        states = self.states()
        self.assertEqual(states["nvim"], "enabled")
        self.assertEqual(states["brew"], "disabled")
        spark = self.states(DOT_PLATFORM="dgx-spark")
        self.assertEqual(spark["llm"], "available")
        self.assertEqual(spark["terminal"], "unsupported")

    def test_add_and_remove_record_state(self):
        result = self.machine.dot("add", "nvim")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual((self.machine.config / "modules").read_text(), "nvim\n")
        self.assertTrue((self.machine.home / ".config/nvim").is_dir())
        self.assertIn("nvim is not installed", result.stdout)
        result = self.machine.dot("remove", "nvim", "brew")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual((self.machine.config / "modules").read_text(), "-nvim\n-brew\n")
        self.assertTrue((self.machine.home / ".config/nvim").is_dir(), "remove must not uninstall")

    def test_add_accepts_flags_and_marks_the_run_as_adding(self):
        module = self.machine.repo / "modules/nvim.sh"
        module.write_text(module.read_text() +
                          'nvim::up() { printf \'adding=%s force=%s\\n\' "${DOT_ADDING:-}" "$DOT_FORCE"; }\n')
        for args in (("add", "nvim"), ("add", "--no-pull", "nvim"), ("add", "nvim", "--force")):
            with self.subTest(args=args):
                result = self.machine.dot(*args)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertIn("adding=true force=true", result.stdout)
                self.assertEqual((self.machine.config / "modules").read_text(), "nvim\n")
        result = self.machine.dot("add", "--bogus", "nvim")
        self.assertEqual(result.returncode, 2)
        self.assertIn("Unknown option: --bogus", result.stderr)

    def test_up_rejects_module_names(self):
        result = self.machine.dot("up", "--no-pull", "shell")
        self.assertEqual(result.returncode, 2)
        self.assertIn("dot run shell", result.stderr)
        self.assertFalse(self.machine.state.exists(), "nothing runs before the arguments are checked")

    def test_list_reads_local_env(self):
        self.machine.config.mkdir(parents=True)
        (self.machine.config / "local.env").write_text("DOT_NODE_VERSION=22\n")
        result = self.machine.dot("list")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Node.js 22", result.stdout)

    def test_unsupported_module_cannot_be_added(self):
        result = self.machine.dot("add", "llm")
        self.assertEqual(result.returncode, 2)
        self.assertIn("not supported on macos", result.stderr)
        self.assertFalse((self.machine.config / "modules").exists())

    def test_selection_order_and_adoption(self):
        spark_dir = self.machine.root / "spark"
        spark_dir.mkdir()
        (spark_dir / ".env").write_text("SPARK_MODE=models\n")
        self.machine.config.mkdir(parents=True)
        (self.machine.config / "modules").write_text("vibemon\n-monitoring\n")
        (spark_dir / ".env.grafana").write_text("x=1\n")
        result = self.machine.shell('''dot_detect
dot_adopt_modules
dot_adopt_modules
dot_selected_modules | tr '\\n' ' '
printf '\\n'
cat "$DOT_CONFIG/modules"
''', DOT_PLATFORM="dgx-spark", DOT_SPARK_DIR=str(spark_dir))
        self.assertEqual(result.returncode, 0, result.stderr)
        lines = result.stdout.splitlines()
        self.assertEqual(lines.count("  ℹ Adopted existing installation: llm"), 1)
        selected = lines[1].split()
        # Profile modules and add-ons run in DOT_MODULE_ORDER, not in file order.
        self.assertEqual(selected, ["base", "apt", "git", "brew", "node", "python", "claude", "shell", "ai",
                                    "llm", "vibemon"])
        self.assertNotIn("monitoring", selected, "a disabled module is never adopted")
        self.assertEqual(lines[2:], ["vibemon", "-monitoring", "llm"])

    def live_lock(self):
        lock = self.machine.state / "run.lock"
        lock.parent.mkdir(parents=True, exist_ok=True)
        sleeper = subprocess.Popen(["sleep", "30"])
        self.addCleanup(lambda: (sleeper.kill(), sleeper.wait()))
        lock.symlink_to(str(sleeper.pid))
        return lock, sleeper

    def test_lock_refuses_live_owner_and_reclaims_stale_lock(self):
        lock, sleeper = self.live_lock()
        result = self.machine.shell('dot_lock && printf locked')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(f"Another dot run is active (pid {sleeper.pid})", result.stderr)
        self.assertEqual(os.readlink(lock), str(sleeper.pid), "a refused run leaves the owner's lock")
        sleeper.kill()
        sleeper.wait()
        result = self.machine.shell('dot_lock && printf "locked %s" "$(readlink "$DOT_LOCKED")" && '
                                    '[ "$(readlink "$DOT_LOCKED")" = "$$" ] && dot_unlock')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(result.stdout.startswith("locked "), result.stdout)
        self.assertFalse(lock.exists() or lock.is_symlink())
        self.assertEqual([p.name for p in lock.parent.iterdir() if p.name.startswith("run.lock")], [])

    def test_reclaim_keeps_a_lock_taken_by_a_concurrent_run(self):
        lock = self.machine.state / "run.lock"
        lock.parent.mkdir(parents=True, exist_ok=True)
        lock.symlink_to("999999")
        # Another run replaces the stale lock between this run's check and its rename.
        result = self.machine.shell(
            'mv() { if [ "$1" = "$DOT_STATE/run.lock" ] && [ "$(readlink "$1")" = 999999 ]; then '
            'rm -f "$1"; ln -s 424242 "$1"; fi; command mv "$@"; }\n'
            'kill() { [ "$2" != 424242 ] && command kill "$@"; }\n'
            'dot_lock && printf locked')
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn("locked", result.stdout)
        self.assertIn("Another dot run started at the same time", result.stderr)
        self.assertEqual(os.readlink(lock), "424242", "the concurrent run keeps its lock")

    def test_directory_at_the_previous_lock_path_does_not_disable_locking(self):
        legacy = self.machine.state / "lock"
        legacy.mkdir(parents=True)
        (legacy / "pid").write_text("1\n")
        lock, sleeper = self.live_lock()
        result = self.machine.shell('dot_lock && printf locked')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(f"Another dot run is active (pid {sleeper.pid})", result.stderr)

    def test_unlock_keeps_a_lock_owned_by_another_process(self):
        lock, sleeper = self.live_lock()
        result = self.machine.shell(f'DOT_LOCKED="{lock}"; dot_unlock; printf "[%s]" "$DOT_LOCKED"')
        self.assertEqual(result.stdout, "[]", result.stderr)
        self.assertEqual(os.readlink(lock), str(sleeper.pid))

    def test_up_refuses_while_locked(self):
        lock, sleeper = self.live_lock()
        result = self.machine.dot("up", "--no-pull")
        self.assertEqual(result.returncode, 1)
        self.assertNotIn("Summary", result.stdout)
        self.assertEqual(os.readlink(lock), str(sleeper.pid))

    def test_module_cli_dispatch(self):
        result = self.machine.dot("llm", "help")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Usage: dot llm", result.stdout)
        result = self.machine.dot("llm", "status")
        self.assertEqual(result.returncode, 2)
        self.assertIn("dot @HOST llm status", result.stderr)
        self.assertEqual(self.machine.dot("nvim").returncode, 2, "modules without ::cli are not commands")


class RemoteTests(unittest.TestCase):
    def setUp(self):
        self.machine = Machine(self)
        self.calls = self.machine.root / "ssh-calls"
        self.machine.stub("ssh", f'''{shlex.quote(sys.executable)} -c 'import json, sys; print(json.dumps(sys.argv[1:]))' "$@" >> "{self.calls}"\n''')

    def ssh(self, *args, **env):
        result = self.machine.dot(*args, **env)
        calls = [json.loads(line) for line in self.calls.read_text().splitlines()] if self.calls.exists() else []
        return result, calls

    def test_alias_destination_and_default_status(self):
        result, calls = self.ssh("@spark")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(calls, [["-o", "ConnectTimeout=10", "-T", "spark", '"$HOME/.dotfiles/bin/dot" status']])

    def test_hosts_file(self):
        identity = self.machine.home / "key"
        identity.write_text("key")
        hosts = self.machine.config / "hosts"
        hosts.mkdir(parents=True)
        (hosts / "spark.env").write_text(f'DOT_HOST=spark-01.example\nDOT_USER=me\nDOT_IDENTITY="~/key"\n'
                                         'DOT_SSH_OPTIONS="-p 2222"\n')
        result, calls = self.ssh("@spark", "llm", "logs", "-f", "llm")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(calls[0], ["-o", "ConnectTimeout=10", "-T", "-p", "2222", "-o", "IdentitiesOnly=yes",
                                    "-i", str(identity), "me@spark-01.example",
                                    '"$HOME/.dotfiles/bin/dot" llm logs -f llm'])

    def test_arguments_survive_the_remote_shell(self):
        tricky = ["a b", "it's", '"quoted"', "$HOME", "*", ""]
        result, calls = self.ssh("@host", "run", *tricky)
        self.assertEqual(result.returncode, 0, result.stderr)
        command = calls[0][-1]
        fake_home = self.machine.root / "remote"
        (fake_home / ".dotfiles/bin").mkdir(parents=True)
        (fake_home / ".dotfiles/bin/dot").write_text('#!/bin/sh\nfor a in "$@"; do printf "<%s>\\n" "$a"; done\n')
        (fake_home / ".dotfiles/bin/dot").chmod(0o755)
        expected = "".join(f"<{arg}>\n" for arg in ["run", *tricky])
        for shell in ("/bin/bash", shutil.which("zsh")):
            if not shell:
                continue
            with self.subTest(shell=shell):
                output = subprocess.run([shell, "-c", command], env={"HOME": str(fake_home), "PATH": "/usr/bin:/bin"},
                                        capture_output=True, text=True, timeout=5)
                self.assertEqual(output.stdout, expected, output.stderr)

    def test_bootstrap(self):
        result, calls = self.ssh("@host", "bootstrap")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(calls[0][-1], "curl -fsSL https://nalbam.github.io/dotfiles/run.sh | bash")

    def test_invalid_input_is_rejected_before_ssh(self):
        hosts = self.machine.config / "hosts"
        hosts.mkdir(parents=True)
        (hosts / "broken.env").write_text("DOT_USER=me\n")
        (hosts / "locked.env").write_text("DOT_HOST=h\nDOT_IDENTITY=/nonexistent/key\n")
        for host, message in (("bad;host", "Invalid host"), ("broken", "DOT_HOST is missing"),
                              ("locked", "not readable")):
            with self.subTest(host=host):
                result, calls = self.ssh("@" + host, "status")
                self.assertEqual(result.returncode, 2)
                self.assertIn(message, result.stderr)
                self.assertEqual(calls, [])


if __name__ == "__main__":
    unittest.main()
