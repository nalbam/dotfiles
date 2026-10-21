#!/usr/bin/env python3
"""Offline tests for run.sh (bootstrap) and lib/repo.sh (checkout sync and archive conversion)."""

import io
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from dot_testlib import ROOT, Machine, module_order  # noqa: E402

RECORDING_DOT = '#!/bin/bash\nprintf "%s\\n" "$@" > "$HOME/dot-args"\n'


def git(*args, cwd=None, env=None):
    return subprocess.run(["git", *args], cwd=cwd, env=env, check=True, capture_output=True, text=True).stdout


class BootstrapTests(unittest.TestCase):
    def setUp(self):
        self.machine = Machine(self, copy=False)
        self.machine.uname("Linux", "x86_64")
        self.calls = self.machine.root / "calls"

    def run_bootstrap(self, *args):
        return subprocess.run(["/bin/bash", str(ROOT / "run.sh"), *args], env=self.machine.env,
                              cwd=self.machine.home, stdin=subprocess.DEVNULL,
                              capture_output=True, text=True, timeout=30)

    def dot_args(self):
        return (self.machine.home / "dot-args").read_text().splitlines()

    def test_help_and_unknown_option_change_nothing(self):
        result = self.run_bootstrap("--help")
        self.assertEqual(result.returncode, 0)
        self.assertIn("Usage: bash run.sh", result.stdout)
        result = self.run_bootstrap("--vbie")
        self.assertEqual(result.returncode, 2)
        self.assertIn("Unknown option: --vbie", result.stderr)
        self.assertEqual(list(self.machine.home.iterdir()), [])

    def stub_git_clone(self):
        self.machine.stub("git", f'''printf '%s\\n' "$*" >> "{self.calls}"
if [ "$1" = clone ]; then
  for target; do :; done
  mkdir -p "$target/bin" && cat > "$target/bin/dot" <<'EOF'
{RECORDING_DOT}EOF
  chmod +x "$target/bin/dot"
fi
''')

    def test_fresh_install_clones_and_runs_dot_up(self):
        self.stub_git_clone()
        result = self.run_bootstrap()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(self.calls.read_text().splitlines(),
                         [f"clone -q https://github.com/nalbam/dotfiles.git {self.machine.repo}"])
        self.assertEqual(self.dot_args(), ["up"])

    def test_options_select_the_dot_command(self):
        self.stub_git_clone()
        self.assertEqual(self.run_bootstrap("--force").returncode, 0)
        self.assertEqual(self.dot_args(), ["up", "--force"])
        self.assertEqual(self.run_bootstrap("--vibe").returncode, 0)
        self.assertEqual(self.dot_args(), ["vibe"])

    def test_archive_install_when_git_is_not_usable(self):
        # macOS without Command Line Tools: /usr/bin/git is the installer stub.
        self.machine.uname("Darwin", "arm64")
        self.machine.stub("xcode-select", "exit 2\n")
        archive = self.machine.root / "main.tar.gz"
        with tarfile.open(archive, "w:gz") as bundle:
            data = RECORDING_DOT.encode()
            info = tarfile.TarInfo("dotfiles-main/bin/dot")
            info.size, info.mode = len(data), 0o755
            bundle.addfile(info, io.BytesIO(data))
        self.machine.stub("curl", f'''printf '%s\\n' "$*" >> "{self.calls}"
while [ "$1" != -o ]; do shift; done
cp "{archive}" "$2"
''')
        if shutil.which("git", path="/usr/bin") != "/usr/bin/git":
            self.skipTest("the macOS Git stub path /usr/bin/git is absent")
        result = self.run_bootstrap()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("Git is not usable yet", result.stdout)
        self.assertIn("codeload.github.com/nalbam/dotfiles", self.calls.read_text())
        self.assertFalse((self.machine.repo / ".git").exists())
        self.assertEqual(self.dot_args(), ["up"])
        self.assertEqual([p.name for p in self.machine.home.iterdir() if p.name.startswith(".dotfiles.")], [])

    def test_failed_archive_download_leaves_no_checkout(self):
        self.machine.uname("Darwin", "arm64")
        self.machine.stub("xcode-select", "exit 2\n")
        self.machine.stub("curl", "exit 22\n")
        self.machine.stub("sleep", "exit 0\n")
        if shutil.which("git", path="/usr/bin") != "/usr/bin/git":
            self.skipTest("the macOS Git stub path /usr/bin/git is absent")
        result = self.run_bootstrap()
        self.assertEqual(result.returncode, 1)
        self.assertIn("Download failed", result.stderr)
        self.assertEqual(list(self.machine.home.iterdir()), [])

    def test_old_layout_checkout_is_pulled(self):
        (self.machine.repo / ".git").mkdir(parents=True)
        self.machine.stub("git", f'''printf '%s\\n' "$*" >> "{self.calls}"
mkdir -p "$2/bin" && printf '%s' '{RECORDING_DOT}' > "$2/bin/dot" && chmod +x "$2/bin/dot"
''')
        result = self.run_bootstrap()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(self.calls.read_text().splitlines(), [f"-C {self.machine.repo} pull --ff-only"])
        self.assertEqual(self.dot_args(), ["up"])

    def test_foreign_directory_is_refused(self):
        self.machine.repo.mkdir()
        (self.machine.repo / "personal").write_text("keep")
        result = self.run_bootstrap()
        self.assertEqual(result.returncode, 1)
        self.assertIn("is not a dotfiles checkout", result.stderr)
        self.assertEqual((self.machine.repo / "personal").read_text(), "keep")


class RepositorySyncTests(unittest.TestCase):
    def setUp(self):
        self.machine = Machine(self, copy=False)
        self.git_env = dict(self.machine.env, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@example.invalid",
                            GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@example.invalid",
                            GIT_CONFIG_NOSYSTEM="1")
        self.origin = self.machine.root / "origin.git"
        self.work = self.machine.root / "work"
        git("init", "-q", "--bare", "-b", "main", str(self.origin), env=self.git_env)
        git("clone", "-q", str(self.origin), str(self.work), env=self.git_env)
        (self.work / "file").write_text("v1\n")
        self.commit("v1")

    def commit(self, message):
        git("add", "-A", cwd=self.work, env=self.git_env)
        git("commit", "-q", "-m", message, cwd=self.work, env=self.git_env)
        git("push", "-q", "origin", "HEAD:main", cwd=self.work, env=self.git_env)

    def sync(self, **env):
        body = '. "$DOT_HOME/lib/repo.sh"\ndot_repo_sync; printf "rc=%s\\n" $?\n'
        result = subprocess.run(["/bin/bash", "-c", f'DOT_HOME="{self.machine.repo}"\n. "{ROOT}/lib/core.sh"\n'
                                 'sleep() { :; }\n' + body.replace('"$DOT_HOME/lib/repo.sh"', f'"{ROOT}/lib/repo.sh"')],
                                env=dict(self.git_env, DOT_REPO_URL=f"file://{self.origin}", **env),
                                capture_output=True, text=True, timeout=30)
        return result

    def test_archive_is_converted_into_a_tracking_checkout(self):
        self.machine.repo.mkdir()
        (self.machine.repo / "file").write_text("v0 archive\n")
        (self.machine.repo / "local-only").write_text("untracked\n")
        result = self.sync()
        self.assertIn("rc=3", result.stdout, result.stdout + result.stderr)
        self.assertEqual((self.machine.repo / "file").read_text(), "v1\n")
        self.assertEqual((self.machine.repo / "local-only").read_text(), "untracked\n")
        upstream = git("-C", str(self.machine.repo), "rev-parse", "--abbrev-ref", "@{upstream}", env=self.git_env)
        self.assertEqual(upstream.strip(), "origin/main")

    def test_pull_reports_changes_and_unchanged_state(self):
        git("clone", "-q", str(self.origin), str(self.machine.repo), env=self.git_env)
        self.assertIn("rc=0", self.sync().stdout)
        (self.work / "file").write_text("v2\n")
        self.commit("v2")
        result = self.sync()
        self.assertIn("rc=3", result.stdout, result.stderr)
        self.assertEqual((self.machine.repo / "file").read_text(), "v2\n")

    def test_pull_failure_warns_and_continues(self):
        git("clone", "-q", str(self.origin), str(self.machine.repo), env=self.git_env)
        git("-C", str(self.machine.repo), "remote", "set-url", "origin", str(self.machine.root / "missing.git"),
            env=self.git_env)
        result = self.sync()
        self.assertIn("rc=0", result.stdout)
        self.assertIn("Pull failed; continuing", result.stdout)

    def test_up_restarts_after_the_checkout_changes(self):
        shutil.rmtree(self.work)
        machine = Machine(self)
        git("init", "-q", "-b", "main", cwd=machine.repo, env=self.git_env)
        git("add", "-A", cwd=machine.repo, env=self.git_env)
        git("commit", "-q", "-m", "base", cwd=machine.repo, env=self.git_env)
        origin = machine.root / "origin.git"
        git("clone", "-q", "--bare", str(machine.repo), str(origin), env=self.git_env)
        git("-C", str(machine.repo), "remote", "add", "origin", str(origin), env=self.git_env)
        git("-C", str(machine.repo), "fetch", "-q", "origin", env=self.git_env)
        git("-C", str(machine.repo), "branch", "-q", "--set-upstream-to=origin/main", "main", env=self.git_env)
        work = machine.root / "work"
        git("clone", "-q", str(origin), str(work), env=self.git_env)
        (work / "NEW").write_text("new\n")
        git("add", "-A", cwd=work, env=self.git_env)
        git("commit", "-q", "-m", "new", cwd=work, env=self.git_env)
        git("push", "-q", "origin", "HEAD:main", cwd=work, env=self.git_env)
        # Disable every module so only the sync and restart are exercised.
        machine.config.mkdir(parents=True)
        (machine.config / "modules").write_text("".join(f"-{name}\n" for name in module_order()))
        git_env = {k: v for k, v in self.git_env.items() if k.startswith("GIT_")}
        result = machine.dot("up", **git_env)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("restarting with the new version", result.stdout)
        self.assertEqual(result.stdout.count("Sync "), 1, "the restarted run must not pull again")
        self.assertEqual(result.stdout.count("Summary"), 1)
        self.assertTrue((machine.repo / "NEW").exists())
        # The restarted run detects the platform again instead of inheriting the
        # value exported by the first run.
        banners = [line for line in result.stdout.splitlines() if "dot · " in line]
        self.assertEqual(len(banners), 2)
        self.assertTrue(all(", detected)" in line for line in banners), banners)

        # A platform chosen by the caller survives the restart.
        (work / "NEWER").write_text("newer\n")
        git("add", "-A", cwd=work, env=self.git_env)
        git("commit", "-q", "-m", "newer", cwd=work, env=self.git_env)
        git("push", "-q", "origin", "HEAD:main", cwd=work, env=self.git_env)
        result = machine.dot("up", DOT_PLATFORM="linux", **git_env)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        banners = [line for line in result.stdout.splitlines() if "dot · " in line]
        self.assertEqual(len(banners), 2)
        self.assertTrue(all(line.strip().startswith("dot · linux") and ", environment)" in line
                            for line in banners), banners)


if __name__ == "__main__":
    unittest.main()
