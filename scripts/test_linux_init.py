#!/usr/bin/env python3
"""Exercise Linux setup sections without root access, networking, or installs."""

import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parent.parent


@unittest.skipUnless(shutil.which("unzip"), "unzip is required for archive tests")
class AWSSetupTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="dotfiles-linux-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.downloads = self.root / "downloads"
        self.downloads.mkdir()
        self.log = self.root / "commands"
        self.archive = self.root / "fixture.zip"
        with zipfile.ZipFile(self.archive, "w") as archive:
            installer = zipfile.ZipInfo("aws/install")
            installer.create_system = 3
            installer.external_attr = 0o100755 << 16
            archive.writestr(installer, '''#!/bin/bash
printf 'install %s\n' "$*" >> "$TEST_LOG"
exit "${TEST_INSTALL_STATUS:-0}"
''')
        source = (ROOT / "linux/init.sh").read_text()
        section = source[source.index("# aws cli"):source.index("# swap")]
        self.script = r'''set -e
aws() {
  printf '%s\n' "${TEST_AWS_VERSION:-aws-cli/1.0.0}"
}
curl() {
  printf 'curl %s\n' "$*" >> "$TEST_LOG"
  if [ "${TEST_CURL_STATUS:-0}" != 0 ]; then return "$TEST_CURL_STATUS"; fi
  cp "$TEST_ARCHIVE" "$4"
}
''' + section + '\nprintf "NEXT_STEP\\n"\n'
        self.env = dict(os.environ, TMPDIR=str(self.downloads), TEST_LOG=str(self.log),
                        TEST_ARCHIVE=str(self.archive))

    def invoke(self, **overrides):
        return subprocess.run(["/bin/bash", "-c", self.script],
                              env=dict(self.env, **overrides), cwd=self.root,
                              stdin=subprocess.DEVNULL, capture_output=True,
                              text=True, timeout=5)

    def assert_clean(self):
        self.assertEqual(list(self.downloads.iterdir()), [])

    def test_existing_v2_skips_download(self):
        result = self.invoke(TEST_AWS_VERSION="aws-cli/2.27.0")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("NEXT_STEP", result.stdout)
        self.assertFalse(self.log.exists())
        self.assert_clean()

    def test_success_installs_archive_and_cleans_downloads(self):
        result = self.invoke()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("NEXT_STEP", result.stdout)
        self.assertIn("install --update", self.log.read_text())
        self.assert_clean()

    def test_installer_failure_cleans_downloads_and_next_run_recovers(self):
        failed = self.invoke(TEST_INSTALL_STATUS="7")
        self.assertEqual(failed.returncode, 7, failed.stderr)
        self.assertNotIn("NEXT_STEP", failed.stdout)
        self.assert_clean()
        recovered = self.invoke()
        self.assertEqual(recovered.returncode, 0, recovered.stderr)
        self.assertIn("NEXT_STEP", recovered.stdout)
        self.assertEqual(self.log.read_text().count("install --update"), 2)
        self.assert_clean()

    def test_download_failure_stops_before_install_and_cleans_up(self):
        result = self.invoke(TEST_CURL_STATUS="22")
        self.assertEqual(result.returncode, 22, result.stderr)
        self.assertNotIn("NEXT_STEP", result.stdout)
        self.assertNotIn("install --update", self.log.read_text())
        self.assert_clean()

    def test_corrupt_archive_stops_before_install_and_cleans_up(self):
        self.archive.write_bytes(b"not a ZIP archive")
        result = self.invoke()
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn("NEXT_STEP", result.stdout)
        self.assertNotIn("install --update", self.log.read_text())
        self.assert_clean()


if __name__ == "__main__":
    unittest.main()
