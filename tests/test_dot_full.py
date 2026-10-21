#!/usr/bin/env python3
"""Run `dot up` end to end offline; only external system commands are simulated."""

import json
import os
from pathlib import Path
import shlex
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from dot_testlib import ROOT, Machine  # noqa: E402

DISPATCHER = r'''import json, os, sys
from pathlib import Path
command, args = Path(sys.argv[1]).name, sys.argv[2:]
home = Path(os.environ["HOME"])
with (home / "commands.jsonl").open("a") as log:
    log.write(json.dumps([command, *args]) + "\n")
platform = os.environ["TEST_OS"]
if command == "uname":
    print(os.environ["TEST_ARCH"] if args == ["-m"] else platform)
elif command == "python3":
    if args[:2] == ["-m", "pip"]:
        toast = Path(os.environ["TEST_STUBS"]) / "toast"
        toast.write_text("#!/bin/sh\necho toast 1.0\n")
        toast.chmod(0o755)
    else:
        os.execv(os.environ["TEST_PYTHON"], [os.environ["TEST_PYTHON"], *args])
elif command == "ssh-keygen":
    target = Path(args[args.index("-f") + 1])
    target.write_text("fixture key, not an SSH key\n")
    target.chmod(0o600)
    target.with_name(target.name + ".pub").write_text("fixture public key\n")
elif command == "git":
    if args[:1] == ["clone"] and args[-2].startswith("https://github.com/dracula/"):
        target = Path(args[-1])
        target.mkdir(parents=True)
        name = "dracula.zsh-theme" if target.name == "zsh" else "Dracula.itermcolors"
        (target / name).write_text("fixture theme\n")
    elif args[:3] == ["-C", str(home / ".dotfiles"), "rev-parse"]:
        print("abc1234")
    else:
        sys.exit("Unexpected Git operation in offline test: %s" % args)
elif command == "curl":
    if args[-1] != "https://raw.githubusercontent.com/ohmyzsh/ohmyzsh/master/tools/install.sh":
        sys.exit("Unexpected network operation in offline test")
    Path(args[args.index("-o") + 1]).write_text(
        'mkdir -p "$HOME/.oh-my-zsh/themes"\nprintf "# fixture\\n" > "$HOME/.oh-my-zsh/oh-my-zsh.sh"\n')
elif command == "dpkg-query":
    print("install ok installed", end="")
elif command == "nvram":
    print("StartupMute\t%01")
elif command == "sysadminctl":
    assert args == ["-screenLock", "status"], args
    print("screenLock delay is immediate", file=sys.stderr)
elif command == "xcode-select":
    assert args == ["-p"], args
elif command == "pgrep":
    assert args == ["-q", "oahd"], args
elif command == "claude":
    assert args in (["update"], ["--version"]), args
elif command == "brew":
    brewfile = str(home / (".dotfiles/packages/Brewfile." + platform.lower()))
    assert args in (["update"], ["upgrade"], ["cleanup"], ["bundle", "--file=" + brewfile]), args
elif command in {"sudo", "apt-get", "chsh", "softwareupdate"}:
    sys.exit("Unexpected privileged operation in offline test: %s %s" % (command, args))
elif command not in {"osascript", "defaults", "chflags", "killall"}:
    sys.exit("Unexpected system command in offline test")
'''

COMMANDS = ("uname", "python3", "ssh-keygen", "git", "curl", "sudo", "apt-get", "dpkg-query", "nvram",
            "sysadminctl", "xcode-select", "pgrep", "softwareupdate", "claude", "brew", "osascript",
            "defaults", "chflags", "killall", "chsh")

NVM = '''nvm() {
  case "$1" in
    version) printf 'v24.99.0\\n' ;;
    install | alias) return 0 ;;
    use) export NVM_BIN="$NVM_DIR/versions/node/v24.99.0/bin"; export PATH="$NVM_BIN:$PATH" ;;
    *) return 99 ;;
  esac
}
'''


class FullRunTests(unittest.TestCase):
    def prepare(self, platform, architecture, dgx=False):
        machine = Machine(self)
        (machine.repo / ".git").mkdir()
        dispatcher = machine.root / "dispatch.py"
        dispatcher.write_text(DISPATCHER)
        for command in COMMANDS:
            machine.stub(command, f'exec {shlex.quote(sys.executable)} {shlex.quote(str(dispatcher))} {command} "$@"\n')
        home = machine.home
        node_bin = home / ".nvm/versions/node/v24.99.0/bin"
        node_bin.mkdir(parents=True)
        (node_bin / "node").write_text('#!/bin/sh\nprintf "v24.99.0\\n"\n')
        (node_bin / "node").chmod(0o755)
        (home / ".nvm/nvm.sh").write_text(NVM)
        for name in (".ssh", ".aws"):
            (home / name).mkdir(mode=0o755)
        for name in (".ssh/config", ".aws/config"):
            (home / name).write_text("machine-specific configuration\n")
            (home / name).chmod(0o600)
        (home / ".profile").write_text("previous shell profile\n")
        machine.env.update(TEST_OS=platform, TEST_ARCH=architecture, TEST_STUBS=str(machine.bin),
                           TEST_PYTHON=sys.executable, SHELL="/bin/zsh", USER="fixture",
                           DOT_BREW_PREFIXES=str(machine.root / "no-brew"),
                           DOT_SYSROOT=str(machine.root / "sysroot"))
        if dgx:
            release = machine.root / "sysroot/etc/dgx-release"
            release.parent.mkdir(parents=True)
            release.write_text('DGX_NAME="DGX Spark"\n')
        return machine

    def commands(self, machine):
        log = machine.home / "commands.jsonl"
        calls = [json.loads(line) for line in log.read_text().splitlines()] if log.exists() else []
        log.write_text("")
        return calls

    def up(self, machine):
        result = machine.dot("up", "--no-pull", timeout=120)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("Summary", result.stdout)
        self.assertNotIn("⚠", result.stdout, result.stdout)
        self.assertNotIn("✗", result.stdout + result.stderr)
        return result

    def check(self, platform, architecture, expected_platform, dgx=False):
        machine = self.prepare(platform, architecture, dgx)
        home, repo = machine.home, machine.repo
        first = self.up(machine)
        self.assertIn(f"dot · {expected_platform}", first.stdout)
        os_dir = platform.lower()
        expected = {".zshrc": "config/shell/zshrc", ".bashrc": "config/shell/bashrc",
                    ".profile": "config/shell/profile", ".aliases": "config/shell/aliases",
                    ".vimrc": "config/vim/vimrc", ".tmux.conf": "config/tmux/tmux.conf",
                    ".zprofile": f"config/shell/zprofile/{os_dir}.{architecture}.sh",
                    ".config/dotfiles/nvm.sh": "config/shell/nvm.sh", ".gitconfig": "config/git/gitconfig",
                    ".codex/AGENTS.md": "codex/AGENTS.md", ".config/opencode/AGENTS.md": "opencode/AGENTS.md",
                    ".agents/skills/docs-sync/SKILL.md": "codex/skills/docs-sync/SKILL.md"}
        for source in (ROOT / "config/git").glob("gitconfig-*"):
            expected["." + source.name] = f"config/git/{source.name}"
        if platform == "Darwin":
            expected[".config/ghostty/config"] = "config/terminal/ghostty.config"
            expected[".iterm2/profiles.json"] = "config/terminal/iterm2-profiles.json"
        for target, source in expected.items():
            with self.subTest(target=target):
                self.assertEqual((home / target).read_bytes(), (repo / source).read_bytes())
        self.assertEqual(os.readlink(home / ".local/bin/dot"), str(repo / "bin/dot"))
        for name in (".ssh/config", ".aws/config"):
            self.assertEqual((home / name).read_text(), "machine-specific configuration\n")
        self.assertEqual((home / ".ssh").stat().st_mode & 0o777, 0o700)
        self.assertEqual((home / ".profile.backup").read_text(), "previous shell profile\n")
        self.assertEqual((home / ".profile.backup").stat().st_mode & 0o777, 0o600)
        calls = self.commands(machine)
        self.assertIn(["claude", "update"], calls)
        self.assertIn(["brew", "bundle", f"--file={repo}/packages/Brewfile.{os_dir}"], calls)
        self.assertEqual(any(call[0] == "defaults" for call in calls), platform == "Darwin")

        stamps = {name: (home / name).stat().st_mtime_ns for name in expected}
        second = self.up(machine)
        self.assertIn("Sync summary: 0 written, 0 pruned", second.stdout)
        self.assertEqual({name: (home / name).stat().st_mtime_ns for name in expected}, stamps)
        self.assertEqual((home / ".profile.backup").read_text(), "previous shell profile\n")
        calls = self.commands(machine)
        self.assertFalse([call for call in calls if call[0] in {"curl", "defaults", "claude", "sudo", "ssh-keygen"}],
                         calls)
        self.assertFalse([call for call in calls if call[:2] in (["brew", "update"], ["brew", "upgrade"],
                                                                  ["brew", "bundle"])], calls)
        return machine

    def test_macos_arm64(self):
        self.check("Darwin", "arm64", "macos")

    def test_linux_x86_64(self):
        self.check("Linux", "x86_64", "linux")

    def test_dgx_spark_without_addons(self):
        machine = self.check("Linux", "aarch64", "dgx-spark", dgx=True)
        self.assertFalse((machine.config / "modules").exists(), "nothing to adopt on a fresh Spark")

    def test_legacy_markers_are_migrated(self):
        machine = self.prepare("Darwin", "arm64")
        toast = machine.home / ".toast"
        toast.mkdir()
        (toast / "macos.applied").write_bytes((ROOT / "config/macos/defaults.sh").read_bytes())
        for name in ("brew", "claude", "pip"):
            (toast / f"last_update_{name}").write_text("9999999999\n")
        (machine.home / ".Brewfile").write_bytes((ROOT / "packages/Brewfile.darwin").read_bytes())
        machine.stub("toast", "echo toast 1.0\n")  # installed earlier, so only the throttle decides
        self.up(machine)
        calls = self.commands(machine)
        self.assertFalse([call for call in calls if call[0] in {"defaults", "claude"}
                          or call[:3] == ["python3", "-m", "pip"]], calls)
        self.assertFalse([call for call in calls if call[0] == "brew"], calls)
        self.assertEqual((machine.state / "stamps/brew").read_text(), "9999999999\n")
        self.assertEqual((machine.state / "stamps/python").read_text(), "9999999999\n")


if __name__ == "__main__":
    unittest.main()
