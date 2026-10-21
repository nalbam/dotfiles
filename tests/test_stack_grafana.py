import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
GRAFANA = ROOT / "stacks" / "grafana"


class DashboardTests(unittest.TestCase):
    def test_spark_service_health_uses_current_model_targets_across_runtimes(self) -> None:
        dashboard = json.loads((GRAFANA / "dashboards/dgx-spark.json").read_text())
        panels = {panel["title"]: panel for panel in dashboard["panels"]}
        for title in ("Service Health", "Active Services", "Workload"):
            query = panels[title]["targets"][0]
            self.assertTrue(query["instant"])
            self.assertFalse(query["range"])
            self.assertIn('service!=""', query["expr"])
            self.assertNotIn('job="vllm"', query["expr"])
            self.assertIn('timestamp(up{', query["expr"])
            self.assertIn('> time() - 45', query["expr"])
        health = panels["Service Health"]["targets"]
        self.assertEqual(len(health), 1)
        self.assertEqual(health[0]["legendFormat"], "{{service}}")
        self.assertTrue(health[0]["expr"].startswith('max by (service) (up{'))

    def test_dashboards_keep_stable_uids_and_portable_variables(self) -> None:
        expected = {"agent-platform": "agent-studio-idc", "dgx-spark": "dgx-spark"}
        for name, uid in expected.items():
            with self.subTest(name=name):
                dashboard = json.loads((GRAFANA / "dashboards" / f"{name}.json").read_text())
                self.assertEqual(dashboard["uid"], uid)
                self.assertEqual(dashboard["refresh"], "10s")
                ids = [panel["id"] for panel in dashboard["panels"]]
                self.assertEqual(len(ids), len(set(ids)))
                variables = {variable["name"]: variable for variable in dashboard["templating"]["list"]}
                self.assertFalse(variables["datasource"]["current"])
                self.assertFalse(variables["instance"]["current"])
                self.assertEqual(variables["instance"]["regex"], "")
                for panel in dashboard["panels"]:
                    if "datasource" in panel:
                        self.assertEqual(panel["datasource"]["uid"], "${datasource}")


class DashboardUploadTests(unittest.TestCase):
    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.calls = self.root / "calls.jsonl"
        binary = self.root / "bin"
        binary.mkdir()
        curl = binary / "curl"
        curl.write_text('''#!/usr/bin/env python3
import json, os, sys
from pathlib import Path
args = sys.argv[1:]
entry = {"args": args}
if "--data-binary" in args:
    entry["payload"] = json.loads(Path(args[args.index("--data-binary") + 1][1:]).read_text())
    code = os.environ.get("TEST_WRITE_STATUS", "200")
    body = {"url": "/d/test/result"}
else:
    code = os.environ.get("TEST_LOOKUP_STATUS", "404")
    body = {"meta": {"folderUid": "existing-folder"}}
with open(os.environ["TEST_CURL_CALLS"], "a") as out:
    out.write(json.dumps(entry) + "\\n")
Path(args[args.index("-o") + 1]).write_text(json.dumps(body))
print(code, end="")
''')
        curl.chmod(0o755)
        self.env = {key: value for key, value in os.environ.items() if not key.startswith("GRAFANA_")}
        self.env.update(PATH=f"{binary}:{os.environ['PATH']}", TEST_CURL_CALLS=str(self.calls))

    def run_upload(self, *args: str, **overrides: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [str(GRAFANA / "upload-dashboard.sh"), *args], cwd=self.root,
            env={**self.env, **overrides}, input="", capture_output=True, text=True, timeout=10,
        )

    def upload(self, **overrides: str) -> subprocess.CompletedProcess[str]:
        return self.run_upload("dgx-spark", **{
            "GRAFANA_URL": "https://grafana.example.test/",
            "GRAFANA_SERVICE_ACCOUNT_TOKEN": "test-token-never-in-argv",
            **overrides,
        })

    def test_dry_run_needs_no_credentials_or_network_from_any_directory(self) -> None:
        for name in ("agent-platform", "dgx-spark"):
            with self.subTest(name=name):
                result = self.run_upload("--dry-run", name)
                self.assertEqual(result.returncode, 0, result.stderr)
                payload = json.loads(result.stdout)
                self.assertIsNone(payload["dashboard"]["id"])
                self.assertEqual(payload["dashboard"]["version"], 0)
                self.assertTrue(payload["overwrite"])
        self.assertFalse(self.calls.exists())

    def test_explicit_file_and_target_settings(self) -> None:
        source = json.loads((GRAFANA / "dashboards/dgx-spark.json").read_text())
        source.update(id=123, version=42)
        path = self.root / "custom dashboard.json"
        path.write_text(json.dumps(source))
        result = self.run_upload(str(path), "--dry-run", GRAFANA_FOLDER_UID="team", GRAFANA_DATASOURCE_UID="prom")
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["folderUid"], "team")
        self.assertIsNone(payload["dashboard"]["id"])
        self.assertEqual(payload["dashboard"]["templating"]["list"][0]["current"]["value"], "prom")
        self.assertEqual(json.loads(path.read_text())["id"], 123)

    def test_create_uses_target_url_and_keeps_token_out_of_arguments(self) -> None:
        result = self.upload()
        self.assertEqual(result.returncode, 0, result.stderr)
        calls = [json.loads(line) for line in self.calls.read_text().splitlines()]
        self.assertEqual(len(calls), 2)
        self.assertEqual(calls[0]["args"][-1], "https://grafana.example.test/api/dashboards/uid/dgx-spark")
        self.assertEqual(calls[1]["payload"]["folderUid"], "")
        self.assertNotIn("test-token-never-in-argv", self.calls.read_text() + result.stdout + result.stderr)
        header_path = calls[0]["args"][calls[0]["args"].index("--header") + 1][1:]
        self.assertFalse(Path(header_path).exists())
        self.assertIn("Dashboard created", result.stdout)

    def test_update_preserves_existing_folder_unless_explicitly_set(self) -> None:
        for overrides, folder in (({}, "existing-folder"), ({"GRAFANA_FOLDER_UID": "team"}, "team"), ({"GRAFANA_FOLDER_UID": ""}, "")):
            with self.subTest(folder=folder):
                result = self.upload(TEST_LOOKUP_STATUS="200", **overrides)
                self.assertEqual(result.returncode, 0, result.stderr)
                last = json.loads(self.calls.read_text().splitlines()[-1])
                self.assertEqual(last["payload"]["folderUid"], folder)
                self.assertIn("Dashboard updated", result.stdout)

    def test_lookup_failure_does_not_write(self) -> None:
        result = self.upload(TEST_LOOKUP_STATUS="403")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("HTTP 403", result.stderr)
        self.assertEqual(len(self.calls.read_text().splitlines()), 1)

    def test_write_failure_is_reported(self) -> None:
        result = self.upload(TEST_WRITE_STATUS="412")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("HTTP 412", result.stderr)
        self.assertNotIn("Dashboard created", result.stdout)

    def test_live_upload_requires_explicit_url_and_token(self) -> None:
        for overrides in ({}, {"GRAFANA_URL": "https://grafana.example.test"}):
            with self.subTest(overrides=overrides):
                result = self.run_upload("dgx-spark", **overrides)
                self.assertNotEqual(result.returncode, 0)
        self.assertFalse(self.calls.exists())

    def test_invalid_arguments_and_dashboard_fail_before_network(self) -> None:
        invalid = self.root / "invalid.json"
        invalid.write_text('{"uid":"../bad", "title":"Bad", "panels":[]}')
        for args in ((), ("--dry-run", "missing"), ("--dry-run", "dgx-spark", "extra"), ("--unknown",), (str(invalid),)):
            with self.subTest(args=args):
                result = self.run_upload(*args)
                self.assertNotEqual(result.returncode, 0)
        self.assertFalse(self.calls.exists())
