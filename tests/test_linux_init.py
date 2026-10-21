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


class SwapSetupTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="dotfiles-swap-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.swapfile = self.root / "swapfile"
        self.fstab = self.root / "fstab"
        self.fstab.touch()
        self.log = self.root / "commands"
        self.active = self.root / "active"
        source = (ROOT / "linux/init.sh").read_text()
        section = source[source.index("# swap"):source.index("mkdir -p /opt/compose")]
        section = section.replace("/swapfile", str(self.swapfile))
        section = section.replace("/etc/fstab", str(self.fstab))
        self.script = r'''set -e
fallocate() {
  printf 'allocate\n' >> "$TEST_LOG"
  printf 'unformatted\n' > "$3"
  return "${TEST_ALLOCATE_STATUS:-0}"
}
mkswap() {
  printf 'format\n' >> "$TEST_LOG"
  if [ "${TEST_FORMAT_STATUS:-0}" != 0 ]; then return "$TEST_FORMAT_STATUS"; fi
  if [ "${TEST_INTERRUPT:-0}" = 1 ]; then
    /bin/sh -c 'kill -TERM "$PPID"'
    return 1
  fi
  printf 'formatted\n' > "$1"
}
swapon() {
  if [ "$1" = --show=NAME ]; then
    if [ -f "$TEST_ACTIVE" ]; then printf '%s\n' "$TEST_SWAPFILE"; fi
  else
    printf 'activate\n' >> "$TEST_LOG"
    if [ "$(cat "$1")" != formatted ]; then return 9; fi
    touch "$TEST_ACTIVE"
  fi
}
''' + section + '\nprintf "NEXT_STEP\\n"\n'
        self.env = dict(os.environ, TEST_LOG=str(self.log), TEST_ACTIVE=str(self.active),
                        TEST_SWAPFILE=str(self.swapfile))

    def invoke(self, **overrides):
        return subprocess.run(["/bin/bash", "-c", self.script],
                              env=dict(self.env, **overrides), cwd=self.root,
                              stdin=subprocess.DEVNULL, capture_output=True,
                              text=True, timeout=5)

    def assert_no_partial_files(self):
        self.assertEqual(list(self.root.glob("swapfile.*")), [])

    def test_fresh_swap_is_formatted_private_and_registered_once(self):
        result = self.invoke()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.swapfile.read_text(), "formatted\n")
        self.assertEqual(self.swapfile.stat().st_mode & 0o777, 0o600)
        self.assertTrue(self.active.exists())
        self.assertEqual(self.log.read_text().splitlines(), ["allocate", "format", "activate"])
        self.assertEqual(self.fstab.read_text(), f"{self.swapfile} none swap sw 0 0\n")
        self.assert_no_partial_files()
        stamp = self.swapfile.stat().st_mtime_ns
        repeated = self.invoke()
        self.assertEqual(repeated.returncode, 0, repeated.stderr)
        self.assertEqual(self.swapfile.stat().st_mtime_ns, stamp)
        self.assertEqual(self.log.read_text().splitlines(), ["allocate", "format", "activate"])
        self.assertEqual(self.fstab.read_text().count(str(self.swapfile)), 1)

    def test_failed_preparation_leaves_no_swapfile_and_can_retry(self):
        for failure in ("TEST_ALLOCATE_STATUS", "TEST_FORMAT_STATUS"):
            with self.subTest(failure=failure):
                self.swapfile.unlink(missing_ok=True)
                self.active.unlink(missing_ok=True)
                self.fstab.write_text("")
                failed = self.invoke(**{failure: "7"})
                self.assertEqual(failed.returncode, 7, failed.stderr)
                self.assertFalse(self.swapfile.exists())
                self.assertFalse(self.active.exists())
                self.assertEqual(self.fstab.read_text(), "")
                self.assert_no_partial_files()
                recovered = self.invoke()
                self.assertEqual(recovered.returncode, 0, recovered.stderr)
                self.assertEqual(self.swapfile.read_text(), "formatted\n")
                self.assertTrue(self.active.exists())
                self.assert_no_partial_files()

    def test_existing_swap_is_activated_without_reformatting(self):
        self.swapfile.write_text("formatted\n")
        before = self.swapfile.stat().st_mtime_ns
        result = self.invoke()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.swapfile.stat().st_mtime_ns, before)
        self.assertEqual(self.log.read_text().splitlines(), ["activate"])
        self.assertTrue(self.active.exists())
        self.assert_no_partial_files()

    def test_interrupted_preparation_does_not_publish_a_swapfile(self):
        interrupted = self.invoke(TEST_INTERRUPT="1")
        self.assertNotEqual(interrupted.returncode, 0)
        self.assertFalse(self.swapfile.exists())
        self.assertFalse(self.active.exists())
        self.assertEqual(self.fstab.read_text(), "")
        recovered = self.invoke()
        self.assertEqual(recovered.returncode, 0, recovered.stderr)
        self.assertEqual(self.swapfile.read_text(), "formatted\n")
        self.assertTrue(self.active.exists())

    def test_existing_non_swap_file_is_preserved_and_failure_is_visible(self):
        self.swapfile.write_text("existing user data\n")
        result = self.invoke()
        self.assertEqual(result.returncode, 9, result.stderr)
        self.assertEqual(self.swapfile.read_text(), "existing user data\n")
        self.assertEqual(self.log.read_text().splitlines(), ["activate"])
        self.assertEqual(self.fstab.read_text(), "")
        self.assertNotIn("NEXT_STEP", result.stdout)
        self.assert_no_partial_files()


if __name__ == "__main__":
    unittest.main()
