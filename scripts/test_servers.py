#!/usr/bin/env python3
"""Check server helper state and real Python HTTP startup in isolated homes."""

import fcntl
import os
from pathlib import Path
import re
import signal
import socket
import subprocess
import sys
import tempfile
import time
import unittest
import urllib.request

ROOT = Path(__file__).resolve().parent.parent
SHELLS = [shell for shell in ("/bin/bash", "/bin/zsh") if Path(shell).is_file()]


class ServerTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="dotfiles-servers-")
        self.addCleanup(temporary.cleanup)
        self.home = Path(temporary.name)
        self.registry = self.home / ".toast/servers"
        fixture_bin = self.home / "bin"
        fixture_bin.mkdir()
        (fixture_bin / "python3").symlink_to(sys.executable)
        self.env = dict(os.environ, HOME=str(self.home),
                        PATH=str(fixture_bin) + ":/usr/bin:/bin:/usr/sbin:/sbin",
                        BASH_ENV="", ENV="", ZDOTDIR=str(self.home))

    def run_shell(self, shell, body):
        args = ["--noprofile", "--norc"] if shell.endswith("bash") else ["-f"]
        return subprocess.run([shell, *args, "-c", '. "$1"\n' + body,
                               "server-test", str(ROOT / "aliases")],
                              cwd=self.home, env=self.env, capture_output=True,
                              text=True, timeout=10)

    def write_registry(self):
        self.registry.parent.mkdir(exist_ok=True)
        self.registry.write_text("8123\tpython\t/example\n")

    def test_node_failure_is_returned_and_registration_removed(self):
        (self.home / "package.json").write_text("{}")
        for shell in SHELLS:
            with self.subTest(shell=shell):
                result = self.run_shell(shell, '''
_port_kill() { return 1; }
np() { printf 'npm\\n'; }
npm() { return 17; }
ss 8123
''')
                self.assertEqual(result.returncode, 17, result.stderr)
                self.assertEqual(self.registry.read_text(), "")

    def test_stop_failure_preserves_registration(self):
        for shell in SHELLS:
            for command in ("sk 8123", "sk all"):
                with self.subTest(shell=shell, command=command):
                    self.write_registry()
                    result = self.run_shell(shell, '''
lsof() { printf '999999\\n'; }
ps() { printf 'example-server\\n'; }
kill() { return 1; }
''' + command)
                    self.assertEqual(result.returncode, 2, result.stderr)
                    self.assertIn("8123", self.registry.read_text())

    def test_list_and_stop_success_return_zero(self):
        for shell in SHELLS:
            for command in ("sl", "sk all"):
                with self.subTest(shell=shell, command=command):
                    self.write_registry()
                    result = self.run_shell(shell, '''
lsof() { printf '999999\\n'; }
ps() { printf 'example-server\\n'; }
kill() { return 0; }
''' + command)
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertIn("example-server", result.stdout)
                    self.assertEqual(bool(self.registry.read_text()), command == "sl")

    def test_invalid_port_does_not_signal_processes(self):
        for shell in SHELLS:
            with self.subTest(shell=shell):
                result = self.run_shell(shell, '''
lsof() { printf 'unexpected lookup' >&2; }
ss 1-65535
''')
                self.assertEqual(result.returncode, 2)
                self.assertNotIn("unexpected lookup", result.stderr)
                self.assertFalse(self.registry.exists())

    def test_registry_tool_failure_preserves_original(self):
        for shell in SHELLS:
            with self.subTest(shell=shell):
                self.write_registry()
                result = self.run_shell(shell, '''
python3() { return 1; }
_server_del 8123
''')
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("8123", self.registry.read_text())

    def test_concurrent_registry_updates_are_serialized(self):
        for shell in SHELLS:
            with self.subTest(shell=shell):
                self.registry.parent.mkdir(exist_ok=True)
                self.registry.write_text("")
                processes = []
                lock_path = self.registry.with_name("servers.lock")
                with lock_path.open("w") as lock:
                    fcntl.flock(lock, fcntl.LOCK_EX)
                    args = ["--noprofile", "--norc"] if shell.endswith("bash") else ["-f"]
                    try:
                        for port in ("8123", "8124"):
                            process = subprocess.Popen(
                                [shell, *args, "-c", '. "$1"; _server_add "$2" python /example',
                                 "server-test", str(ROOT / "aliases"), port],
                                cwd=self.home, env=self.env, stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE, text=True,
                            )
                            processes.append(process)
                        time.sleep(0.15)
                        self.assertTrue(all(process.poll() is None for process in processes))
                        self.assertEqual(self.registry.read_text(), "")
                        fcntl.flock(lock, fcntl.LOCK_UN)
                        for process in processes:
                            stdout, stderr = process.communicate(timeout=5)
                            self.assertEqual(process.returncode, 0, stdout + stderr)
                    finally:
                        fcntl.flock(lock, fcntl.LOCK_UN)
                        for process in processes:
                            if process.poll() is None:
                                process.kill()
                            process.communicate(timeout=5)
                self.assertEqual({row.split("\t")[0] for row in self.registry.read_text().splitlines()},
                                 {"8123", "8124"})

    def test_invalid_registry_record_preserves_original(self):
        self.write_registry()
        for shell in SHELLS:
            with self.subTest(shell=shell):
                result = self.run_shell(shell, "_server_add 8124 python $'bad\\npath'\n")
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(self.registry.read_text(), "8123\tpython\t/example\n")

    def test_registry_missing_final_newline_does_not_join_records(self):
        for shell in SHELLS:
            with self.subTest(shell=shell):
                self.write_registry()
                self.registry.write_text("8123\tpython\t/example")
                result = self.run_shell(shell, "_server_add 8124 python /second\n")
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(self.registry.read_text().splitlines(),
                                 ["8123\tpython\t/example", "8124\tpython\t/second"])

    def test_python_startup_failure_is_visible(self):
        (self.home / "docs").mkdir()
        for shell in SHELLS:
            with self.subTest(shell=shell):
                result = self.run_shell(shell, '''
_port_kill() { return 1; }
python3() { printf 'python startup failed\\n' >&2; return 29; }
ss 8123
''')
                self.assertEqual(result.returncode, 29, result.stderr)
                self.assertIn("python startup failed", result.stderr)
                self.assertNotIn("Serving", result.stdout)
                self.assertFalse(self.registry.exists())

    def test_python_bind_failure_is_visible(self):
        (self.home / "docs").mkdir()
        with socket.socket() as listener:
            listener.bind(("", 0))
            listener.listen()
            port = listener.getsockname()[1]
            for shell in SHELLS:
                with self.subTest(shell=shell):
                    result = self.run_shell(shell, '_port_kill() { return 1; }\nss ' + str(port))
                    if match := re.search(r"\(PID (\d+)\)", result.stdout):
                        os.kill(int(match.group(1)), signal.SIGTERM)
                    self.assertNotEqual(result.returncode, 0, result.stdout)
                    self.assertIn("Address already in use", result.stderr)
                    self.assertNotIn("Serving", result.stdout)
                    self.assertFalse(self.registry.exists())

    def test_python_success_means_http_is_ready(self):
        docs = self.home / "docs"
        docs.mkdir()
        (docs / "index.html").write_text("server ready")
        for shell in SHELLS:
            with self.subTest(shell=shell):
                with socket.socket() as reservation:
                    reservation.bind(("127.0.0.1", 0))
                    port = reservation.getsockname()[1]
                result = self.run_shell(shell, '_port_kill() { return 1; }\nss ' + str(port))
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                pid = int(re.search(r"\(PID (\d+)\)", result.stdout).group(1))
                try:
                    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
                    with opener.open(f"http://127.0.0.1:{port}/", timeout=3) as response:
                        self.assertEqual(response.read(), b"server ready")
                    self.assertIn(str(port), self.registry.read_text())
                finally:
                    os.kill(pid, signal.SIGTERM)


if __name__ == "__main__":
    unittest.main()
