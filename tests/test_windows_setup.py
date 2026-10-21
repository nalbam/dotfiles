#!/usr/bin/env python3
"""Run the PowerShell entrypoint with mocked links and winget when available."""

import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parent.parent
POWERSHELL = shutil.which("pwsh") or shutil.which("powershell")


@unittest.skipUnless(POWERSHELL, "PowerShell is not installed")
class WindowsSetupTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="dotfiles-windows-")
        self.addCleanup(self.temp.cleanup)
        self.wrapper = Path(self.temp.name) / "invoke.ps1"
        self.wrapper.write_text(r'''
function Test-Path {
    param([string]$Path)
    return $Path -eq "$HOME\.dotfiles"
}
function New-Item {
    [CmdletBinding()]
    param($ItemType, $Path, $Target)
    if ($env:TEST_LINK_FAILURE -eq "1") {
        Write-Error "Mock link creation failure"
        return
    }
    @{ Path = $Path; Target = $Target } | ConvertTo-Json -Compress |
        Add-Content -LiteralPath $env:TEST_LINK_LOG -Encoding utf8
    Write-Host "MOCK_LINK"
}
function winget {
    if ($args[0] -eq "list") {
        if ($env:TEST_INSTALLED -eq "1") {
            Write-Output $args[2]
            $global:LASTEXITCODE = 0
        } else {
            $global:LASTEXITCODE = 1
        }
    } elseif ($args[0] -eq "install") {
        Write-Host "MOCK_INSTALL"
        $global:LASTEXITCODE = [int]$env:TEST_INSTALL_STATUS
    } else {
        throw "Unexpected winget command"
    }
}
try {
    & $env:DOTFILES_SCRIPT
    Write-Host "SETUP_RETURNED"
} catch {
    [Console]::Error.WriteLine($_.ToString())
    exit 1
}
''', encoding="utf-8")

    def invoke(self, **overrides):
        env = dict(os.environ, DOTFILES_SCRIPT=str(ROOT / "run.ps1"),
                   TEST_LINK_LOG=str(Path(self.temp.name) / "links.jsonl"),
                   TEST_INSTALL_STATUS="0", TEST_INSTALLED="0", TEST_LINK_FAILURE="0")
        env.update(overrides)
        return subprocess.run([POWERSHELL, "-NoLogo", "-NoProfile", "-NonInteractive",
                               "-File", str(self.wrapper)], env=env,
                              capture_output=True, text=True, timeout=15)

    def test_success_creates_links_and_installs_packages(self):
        result = self.invoke()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.count("MOCK_LINK"), len(list((ROOT / "config/git").glob("gitconfig*"))) + 1)
        self.assertEqual(result.stdout.count("MOCK_INSTALL"), 2)
        self.assertIn("SETUP_RETURNED", result.stdout)

    def test_linked_git_profiles_select_directory_identities(self):
        result = self.invoke()
        self.assertEqual(result.returncode, 0, result.stderr)
        home = Path(self.temp.name) / "machine home"
        home.mkdir()
        # Materialize the actual New-Item requests in a private home. This also
        # works on macOS/Linux CI without touching PowerShell's real HOME.
        records = (Path(self.temp.name) / "links.jsonl").read_text(encoding="utf-8-sig").splitlines()
        for line in records:
            link = json.loads(line)
            name = Path(link["Path"].replace("\\", "/")).name
            source = ROOT / "config" / link["Target"].replace("\\", "/").split("/config/", 1)[1]
            self.assertTrue(source.is_file())
            (home / name).symlink_to(source)
        env = dict(os.environ, HOME=str(home), GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=str(home / ".gitconfig"))
        for account, profile in (("nalbam", "nalbam"), ("opspresso", "nalbam"),
                                 ("yujh404", "yujh404"), ("nalbam-me", "nalbam-me"),
                                 ("nalbam-bot", "nalbam-bot")):
            with self.subTest(account=account):
                workspace = home / "workspace/github.com" / account / "example"
                subprocess.run(["git", "init", "-q", str(workspace)], env=env, check=True)
                for key in ("user.name", "user.email"):
                    actual = subprocess.check_output(["git", "-C", str(workspace), "config", "--get", key], env=env)
                    expected = subprocess.check_output(["git", "config", "--file", str(ROOT / "config/git" / ("gitconfig-" + profile)), "--get", key], env=env)
                    self.assertTrue(actual == expected, f"Incorrect {key} for {profile}")

    def test_installed_packages_skip_installation(self):
        result = self.invoke(TEST_INSTALLED="1")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn("MOCK_INSTALL", result.stdout)
        self.assertIn("SETUP_RETURNED", result.stdout)

    def test_link_failure_stops_before_package_installation(self):
        result = self.invoke(TEST_LINK_FAILURE="1")
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn("MOCK_INSTALL", result.stdout)
        self.assertNotIn("SETUP_RETURNED", result.stdout)

    def test_package_failure_stops_before_completion(self):
        result = self.invoke(TEST_INSTALL_STATUS="7")
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(result.stdout.count("MOCK_INSTALL"), 1)
        self.assertNotIn("SETUP_RETURNED", result.stdout)


if __name__ == "__main__":
    unittest.main()
