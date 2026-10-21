"""Shared fixtures for the dot CLI tests: a copied checkout, a temporary home and command stubs."""

import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parent.parent


def copy_checkout(target):
    """Copy the tracked files (working-tree content) into TARGET."""
    tracked = subprocess.check_output(["git", "ls-files", "-z"], cwd=ROOT).decode().split("\0")
    for name in filter(None, tracked):
        source = ROOT / name
        if not source.exists() and not source.is_symlink():
            continue
        destination = target / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        if source.is_symlink():
            destination.symlink_to(os.readlink(source))
        else:
            shutil.copy2(source, destination)
    return target


def clean_env(**overrides):
    env = {key: value for key, value in os.environ.items() if not key.startswith("BASH_FUNC_")}
    for key in list(env):
        if key.startswith(("DOT_", "NVM_", "XDG_", "GCLOUD_", "VIBEMON_")) or key in (
                "BREWPATH", "WSL_DISTRO_NAME", "SSH_AUTH_SOCK"):
            env.pop(key)
    env.update(TERM="dumb", BASH_ENV="", DOT_COLOR="false", PYTHONIOENCODING="utf-8")
    env.update(overrides)
    return env


def write_stub(directory, name, body):
    """Write an executable shell stub NAME into DIRECTORY."""
    path = Path(directory) / name
    path.write_text("#!/bin/sh\n" + body)
    path.chmod(0o755)
    return path


def python_stub(directory, name, source):
    """Write an executable that runs the Python SOURCE with the current interpreter."""
    script = Path(directory) / f".{name}.py"
    script.write_text(source)
    return write_stub(directory, name,
                      f'exec {shlex.quote(sys.executable)} {shlex.quote(str(script))} "$0" "$@"\n')


class Machine:
    """A temporary home with a copied checkout at ~/.dotfiles and a stub bin directory."""

    def __init__(self, testcase, copy=True):
        temporary = tempfile.TemporaryDirectory(prefix="dot-test-")
        testcase.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.home = self.root / "machine home"
        self.repo = self.home / ".dotfiles"
        self.bin = self.root / "stubs"
        self.bin.mkdir()
        self.home.mkdir()
        if copy:
            copy_checkout(self.repo)
        self.env = clean_env(HOME=str(self.home), PATH=f"{self.bin}:/usr/bin:/bin:/usr/sbin:/sbin",
                             TMPDIR=str(self.root))

    def stub(self, name, body):
        return write_stub(self.bin, name, body)

    def uname(self, system, machine):
        self.stub("uname", f'''case "$1" in
  -m) printf '%s\\n' {shlex.quote(machine)} ;;
  *) printf '%s\\n' {shlex.quote(system)} ;;
esac
''')

    def dot(self, *args, input=None, timeout=60, **env):
        return subprocess.run(["/bin/bash", str(self.repo / "bin/dot"), *args],
                              env=dict(self.env, **env), cwd=self.home, input=input,
                              capture_output=True, text=True, timeout=timeout)

    def shell(self, body, timeout=30, **env):
        """Run BODY with the libraries loaded from the copied checkout."""
        prelude = f'''DOT_HOME={shlex.quote(str(self.repo))}
. "$DOT_HOME/lib/core.sh"; . "$DOT_HOME/lib/detect.sh"; . "$DOT_HOME/lib/modules.sh"
sleep() {{ :; }}
'''
        return subprocess.run(["/bin/bash", "-c", prelude + body], env=dict(self.env, **env),
                              cwd=self.home, capture_output=True, text=True, timeout=timeout)

    @property
    def config(self):
        return self.home / ".config/dotfiles"

    @property
    def state(self):
        return self.home / ".local/state/dotfiles"
