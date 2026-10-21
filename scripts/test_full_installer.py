#!/usr/bin/env python3
"""Run every installer step offline; only external system commands are simulated."""

import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parent.parent


class FullInstallerTests(unittest.TestCase):
    def check_installation(self, platform, architecture):
        with tempfile.TemporaryDirectory(prefix="dotfiles-full-install-") as directory:
            home = Path(directory) / "machine home"
            repo = home / ".dotfiles"
            repo.mkdir(parents=True)
            tracked = subprocess.check_output(["git", "ls-files", "-z"], cwd=ROOT).decode().split("\0")
            for name in filter(None, tracked):
                source, target = ROOT / name, repo / name
                target.parent.mkdir(parents=True, exist_ok=True)
                if source.is_symlink():
                    target.symlink_to(source.readlink())
                else:
                    shutil.copy2(source, target)

            binary = home / "bin"
            binary.mkdir()
            dispatcher = home / "system_commands.py"
            dispatcher.write_text(r'''import hashlib, json, os, sys
from pathlib import Path
command, args = Path(sys.argv[1]).name, sys.argv[2:]
home = Path(os.environ["HOME"])
with (home / "commands.jsonl").open("a") as log:
    log.write(json.dumps([command, *args]) + "\n")
if command == "uname":
    print(os.environ["TEST_ARCH"] if args == ["-m"] else os.environ["TEST_OS"])
elif command in {"md5", "md5sum"}:
    digest = hashlib.md5(Path(args[-1]).read_bytes()).hexdigest()
    print(digest if command == "md5" else digest + "  " + args[-1])
elif command == "python3":
    if args[:2] != ["-m", "pip"]:
        os.execv(sys.executable, [sys.executable, *args])
elif command == "ssh-keygen":
    target = Path(args[args.index("-f") + 1])
    target.write_text("fixture key, not an SSH key\n")
    target.chmod(0o600)
    target.with_name(target.name + ".pub").write_text("fixture public key\n")
elif command == "git":
    if args[0] == "clone" and args[1].startswith("https://github.com/dracula/"):
        target = Path(args[-1])
        target.mkdir(parents=True)
        name = "dracula.zsh-theme" if target.name == "zsh" else "Dracula.itermcolors"
        (target / name).write_text("fixture theme\n")
    elif args != ["-C", str(home / ".dotfiles"), "pull"]:
        sys.exit("Unexpected Git operation in offline test")
elif command == "curl":
    if args[-1] != "https://raw.githubusercontent.com/ohmyzsh/ohmyzsh/master/tools/install.sh":
        sys.exit("Unexpected network operation in offline test")
    Path(args[args.index("-o") + 1]).write_text('mkdir -p "$HOME/.oh-my-zsh/themes"\nprintf "# fixture\\n" > "$HOME/.oh-my-zsh/oh-my-zsh.sh"\n')
elif command == "sudo":
    if not args or args[0] != "apt" or args[1] not in {"update", "install"}:
        sys.exit("Unexpected privileged operation in offline test")
elif command == "dpkg-query":
    print("install ok installed\n" * (len(args) - 2), end="")
elif command == "nvram":
    assert args == ["StartupMute"]
    print("StartupMute\t%01")
elif command == "sysadminctl":
    assert args == ["-screenLock", "status"]
    print("screenLock delay is immediate", file=sys.stderr)
elif command == "xcode-select":
    assert args == ["-p"]
elif command == "pgrep":
    assert args == ["-q", "oahd"]
elif command == "getopt":
    print("--")
elif command == "claude":
    assert args == ["update"]
elif command == "brew":
    bundle = ["bundle", "--file=" + str(home / ".dotfiles" / os.environ["TEST_OS"].lower() / "Brewfile")]
    assert args in (["update"], ["upgrade"], ["cleanup"], ["link", "--force", "gnu-getopt"], bundle)
elif command not in {"tput", "osascript", "defaults", "chflags"}:
    sys.exit("Unexpected system command in offline test")
''')
            commands = ("uname", "md5", "md5sum", "python3", "ssh-keygen", "git", "curl", "sudo",
                        "dpkg-query", "nvram", "sysadminctl", "xcode-select", "pgrep", "getopt",
                        "claude", "brew", "tput", "osascript", "defaults", "chflags",
                        "killall", "chsh", "softwareupdate", "apt")
            for command in commands:
                wrapper = binary / command
                wrapper.write_text("#!/bin/sh\nexec " + shlex.quote(sys.executable) + " " +
                                   shlex.quote(str(dispatcher)) + ' "$0" "$@"\n')
                wrapper.chmod(0o755)

            node_bin = home / ".nvm/versions/node/v24.99.0/bin"
            node_bin.mkdir(parents=True)
            (node_bin / "node").write_text('#!/bin/sh\nprintf "v24.99.0\\n"\n')
            (node_bin / "node").chmod(0o755)
            (home / ".nvm/nvm.sh").write_text('''nvm() {
  case "$1" in
    version) printf 'v24.99.0\\n' ;;
    alias) return 0 ;;
    use) export NVM_BIN="$NVM_DIR/versions/node/v24.99.0/bin" ;;
    *) return 99 ;;
  esac
}
''')
            for name in (".ssh", ".aws", "tmp"):
                (home / name).mkdir()
            for name in (".ssh/config", ".aws/config"):
                (home / name).write_text("machine-specific configuration\n")
                (home / name).chmod(0o600)
            (home / ".profile").write_text("previous shell profile\n")
            env = {"HOME": str(home), "PATH": str(binary) + ":/usr/bin:/bin:/usr/sbin:/sbin",
                   "SHELL": "/bin/zsh", "USER": "fixture", "TERM": "dumb", "BASH_ENV": "",
                   "TMPDIR": str(home / "tmp"), "TEST_OS": platform, "TEST_ARCH": architecture,
                   "PYTHONIOENCODING": "utf-8"}

            def install():
                result = subprocess.run(["/bin/bash", str(repo / "run.sh")], env=env,
                                        cwd=home, capture_output=True, text=True, timeout=60)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertIn("[11/11]", result.stdout)
                self.assertIn("INSTALLATION COMPLETED", result.stdout)
                self.assertNotIn("⚠", result.stdout)
                self.assertEqual(result.stderr, "")
                return result

            install()
            os_dir = platform.lower()
            expected = {".profile": "profile", ".bashrc": "bashrc", ".zshrc": "zshrc", ".aliases": "aliases",
                        ".zprofile": f"{os_dir}/zprofile.{architecture}.sh", ".Brewfile": f"{os_dir}/Brewfile",
                        ".config/dotfiles/nvm.sh": "shell/nvm.sh", ".codex/AGENTS.md": "codex/AGENTS.md",
                        ".config/opencode/AGENTS.md": "opencode/AGENTS.md",
                        ".agents/skills/docs-sync/SKILL.md": "codex/skills/docs-sync/SKILL.md"}
            for target, source in expected.items():
                self.assertEqual((home / target).read_bytes(), (repo / source).read_bytes())
            for name in (".ssh/config", ".aws/config"):
                self.assertEqual((home / name).read_text(), "machine-specific configuration\n")
            self.assertEqual((home / ".ssh").stat().st_mode & 0o777, 0o700)
            self.assertEqual((home / ".profile.backup").read_text(), "previous shell profile\n")
            self.assertEqual((home / ".profile.backup").stat().st_mode & 0o777, 0o600)
            self.assertEqual((home / ".toast/macos.applied").exists(), platform == "Darwin")
            calls = [json.loads(line) for line in (home / "commands.jsonl").read_text().splitlines()]
            self.assertEqual(any(call[0] == "defaults" for call in calls), platform == "Darwin")
            stamps = {name: (home / name).stat().st_mtime_ns for name in expected}
            (home / "commands.jsonl").write_text("")
            repeated = install()
            self.assertIn("Sync summary: 0 written, 0 pruned", repeated.stdout)
            self.assertEqual({name: (home / name).stat().st_mtime_ns for name in expected}, stamps)
            self.assertEqual((home / ".profile.backup").read_text(), "previous shell profile\n")
            calls = [json.loads(line) for line in (home / "commands.jsonl").read_text().splitlines()]
            self.assertFalse(any(call[0] in {"curl", "defaults", "claude", "sudo", "ssh-keygen"} for call in calls))
            self.assertFalse(any(call[:2] in (["brew", "update"], ["brew", "upgrade"], ["brew", "bundle"]) for call in calls))

    def test_macos_full_install_and_repeat(self):
        self.check_installation("Darwin", "arm64")

    def test_linux_full_install_and_repeat(self):
        self.check_installation("Linux", "x86_64")


if __name__ == "__main__":
    unittest.main()
