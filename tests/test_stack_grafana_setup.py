"""Run setup-grafana.sh with stubbed Docker, curl, and host name."""

import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
ACCOUNT = {
    "GCLOUD_FM_URL": "https://fleet.example.net",
    "GCLOUD_FM_USERNAME": "1001",
    "GCLOUD_PROM_URL": "https://prom.example.net/api/prom/push",
    "GCLOUD_PROM_USERNAME": "2002",
}


class GrafanaSetupTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.spark = self.root / "spark"
        shutil.copytree(ROOT / "stacks/dgx-spark", self.spark)
        binary = self.root / "bin"
        binary.mkdir()
        programs = {
            "docker": "#!/bin/sh\nexit 0\n",
            "hostname": "#!/bin/sh\necho test-host\n",
            "sleep": "#!/bin/sh\nexit 0\n",
            "curl": f'''#!{sys.executable}
import sys
from pathlib import Path
args = sys.argv[1:]
if "--output" in args:
    Path(args[args.index("--output") + 1]).write_text("DCGM_FI_DEV_GPU_UTIL 1\\n")
''',
            "python3": f'''#!{sys.executable}
import os, sys
if any(arg.endswith("services.py") for arg in sys.argv[1:]):
    sys.exit(0)
os.execv("{sys.executable}", ["{sys.executable}", *sys.argv[1:]])
''',
        }
        for name, content in programs.items():
            (binary / name).write_text(content)
            (binary / name).chmod(0o755)
        self.env = {key: value for key, value in os.environ.items() if not key.startswith("GCLOUD_")}
        self.env["PATH"] = f"{binary}:{os.environ['PATH']}"

    def run_setup(self, **values):
        return subprocess.run([str(self.spark / "scripts/setup-grafana.sh")], env={**self.env, **values},
                              stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=20)

    def stored(self):
        lines = (self.spark / ".env.grafana").read_text().splitlines()
        return {key: value.strip('"') for key, _, value in (line.partition("=") for line in lines)}

    def test_new_setup_stores_account_values_and_host_collector(self):
        result = self.run_setup(GCLOUD_RW_API_KEY="token", **ACCOUNT)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.stored(), {**ACCOUNT, "GCLOUD_FM_COLLECTOR_ID": "test-host", "GCLOUD_RW_API_KEY": "token"})
        self.assertEqual((self.spark / ".env.grafana").stat().st_mode & 0o777, 0o600)

    def test_existing_file_keeps_secret_and_collector_when_adding_account_values(self):
        (self.spark / ".env.grafana").write_text('GCLOUD_RW_API_KEY="kept"\nGCLOUD_FM_COLLECTOR_ID="old-id"\n')
        result = self.run_setup(**ACCOUNT)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.stored()["GCLOUD_RW_API_KEY"], "kept")
        self.assertEqual(self.stored()["GCLOUD_FM_COLLECTOR_ID"], "old-id")
        self.assertEqual(self.stored()["GCLOUD_PROM_USERNAME"], "2002")

    def test_missing_account_value_fails_without_a_terminal(self):
        (self.spark / ".env.grafana").write_text('GCLOUD_RW_API_KEY="kept"\n')
        result = self.run_setup()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("GCLOUD_FM_URL is required in non-interactive mode", result.stderr)
        self.assertEqual((self.spark / ".env.grafana").read_text(), 'GCLOUD_RW_API_KEY="kept"\n')

    def test_invalid_account_values_are_rejected(self):
        for key, value, message in (("GCLOUD_FM_USERNAME", "12a", "must contain only digits"),
                                    ("GCLOUD_PROM_URL", "http://prom.example.net", "must be an HTTPS URL")):
            with self.subTest(key=key):
                result = self.run_setup(GCLOUD_RW_API_KEY="token", **{**ACCOUNT, key: value})
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(f"{key} {message}", result.stderr)
                self.assertFalse((self.spark / ".env.grafana").exists())


if __name__ == "__main__":
    unittest.main()
