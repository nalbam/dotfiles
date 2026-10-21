import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class SparkDeploymentTests(unittest.TestCase):
    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.spark = self.root / "spark"
        shutil.copytree(ROOT / "stacks/dgx-spark", self.spark,
                        ignore=shutil.ignore_patterns(".env", ".env.grafana", "backups"))
        binary = self.root / "bin"
        binary.mkdir()
        self.calls = self.root / "docker.jsonl"
        self.config = self.root / "compose.json"
        self.services = {
            "comfyui": {"profiles": ["comfyui"], "image": "example/comfyui:v1"},
        }
        for name, port in (("llm", 8000), ("embedding", 8001), ("reranker", 8002)):
            self.services[name] = {
                "profiles": ["models"], "image": "example/model:v1",
                "healthcheck": {"test": ["CMD", "curl", "-f", f"http://localhost:{port}/health"]},
                "labels": {"io.dockpad.hf-model": f"example/{name}", "io.dockpad.metrics-port": str(port)},
                "ports": [{"host_ip": "127.0.0.1", "target": port, "published": str(port)}],
            }
            self.services[name]["labels"]["io.dockpad.api-kind"] = "chat" if name == "llm" else name
        self.services["embedding"]["depends_on"] = {"llm": {"condition": "service_healthy"}}
        self.services["reranker"]["depends_on"] = {"embedding": {"condition": "service_healthy"}}
        self.services["flash"] = {
            "profiles": ["flash"], "image": "example/tensorfold:v1",
            "healthcheck": {"test": ["CMD", "python3", "/opt/dockpad/flash-health.py"]},
            "labels": {"io.dockpad.hf-model": "example/flash", "io.dockpad.metrics-port": "8000",
                       "io.dockpad.metrics-job": "vllm", "io.dockpad.api-kind": "chat"},
            "ports": [{"host_ip": "127.0.0.1", "target": 8000, "published": "8000"}],
        }
        self.config.write_text(json.dumps({"services": self.services}))
        programs = {
            "uname": '#!/usr/bin/env bash\necho aarch64\n',
            "nvidia-smi": '#!/usr/bin/env bash\nexit 0\n',
            "systemctl": '#!/usr/bin/env bash\nexit 0\n',
            "tailscale": '#!/usr/bin/env bash\nif [[ "$1" == ip ]]; then echo 100.100.100.100; fi\n',
            "curl": '''#!/usr/bin/env python3
import json, os, sys
from pathlib import Path
args = sys.argv[1:]
with open(os.environ["TEST_HTTP_CALLS"], "a") as output:
    output.write(args[-1] + "\\n")
if "--output" in args:
    body = json.dumps({"devices": [{"type": "cuda"}]}) if args[-1].endswith("system_stats") else "vllm:num_requests_running 0\\n"
    Path(args[args.index("--output") + 1]).write_text(body)
''',
            "docker": '''#!/usr/bin/env python3
import json, os, sys
from pathlib import Path
args = sys.argv[1:]
with open(os.environ["TEST_DOCKER_CALLS"], "a") as output:
    output.write(json.dumps(args) + "\\n")
if "run" in args:
    # Compose attaches stdin even with -T; it must not consume the snapshot list.
    sys.stdin.read()
if "config" in args:
    services = json.loads(Path(os.environ["TEST_COMPOSE_CONFIG"]).read_text())["services"]
    profiles = [args[i + 1] for i, arg in enumerate(args) if arg == "--profile"]
    active = {name: service for name, service in services.items() if "*" in profiles or set(profiles).intersection(service["profiles"])}
    if "--services" in args:
        print("\\n".join(active))
    elif "--format" in args:
        print(json.dumps({"services": active}))
elif "ps" in args and "-q" in args:
    print("test-" + args[-2])
elif args[0] == "inspect":
    if "Health" in args[2]:
        print("unhealthy" if args[-1] == "test-" + os.environ.get("TEST_FAIL_HEALTH", "") else "healthy")
    else:
        print("running")
elif "build" in args and os.environ.get("TEST_FAIL_BUILD") == "true":
    raise SystemExit(1)
elif "run" in args and os.environ.get("TEST_FAIL_DOWNLOAD") == "true":
    raise SystemExit(1)
''',
        }
        for name, content in programs.items():
            path = binary / name
            path.write_text(content)
            path.chmod(0o755)
        self.http_calls = self.root / "http.txt"
        self.env = {**os.environ, "PATH": f"{binary}:{os.environ['PATH']}",
                    "XDG_CONFIG_HOME": str(self.root / "config"),
                    "TEST_DOCKER_CALLS": str(self.calls), "TEST_HTTP_CALLS": str(self.http_calls),
                    "TEST_COMPOSE_CONFIG": str(self.config),
                    "DRY_RUN": "true"}
        for key in ("ONLY", "COMPOSE_PROFILES"):
            self.env.pop(key, None)

    def deploy(self, mode: str, service: str, **overrides: str) -> subprocess.CompletedProcess[str]:
        (self.spark / ".env").write_text(
            f"SPARK_MODE={mode}\nCOMFYUI_DATA_PATH={self.root}/data\n"
        )
        return subprocess.run(
            [str(self.spark / "scripts/deploy.sh")], env={**self.env, "ONLY": service, **overrides},
            capture_output=True, text=True, timeout=10,
        )

    def test_incomplete_grafana_environment_stops_before_compose(self) -> None:
        (self.spark / ".env.grafana").write_text('GCLOUD_RW_API_KEY="token"\nGCLOUD_FM_COLLECTOR_ID="host"\n')
        result = self.deploy("models", "llm", DRY_RUN="false")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(".env.grafana is missing: GCLOUD_FM_URL GCLOUD_FM_USERNAME GCLOUD_PROM_URL GCLOUD_PROM_USERNAME",
                      result.stderr)
        for call in map(json.loads, self.calls.read_text().splitlines()):
            self.assertEqual(call[:2] if call[:1] == ["compose"] else ["compose", "version"], ["compose", "version"], call)

    def test_complete_grafana_environment_enables_monitoring_profile(self) -> None:
        (self.spark / ".env.grafana").write_text("".join(
            f'{key}="{value}"\n' for key, value in (
                ("GCLOUD_FM_URL", "https://fleet.example"), ("GCLOUD_FM_USERNAME", "1"),
                ("GCLOUD_PROM_URL", "https://prom.example/api/prom/push"), ("GCLOUD_PROM_USERNAME", "2"),
                ("GCLOUD_FM_COLLECTOR_ID", "host"), ("GCLOUD_RW_API_KEY", "token"))))
        result = self.deploy("models", "llm")
        self.assertEqual(result.returncode, 0, result.stderr)
        calls = [json.loads(line) for line in self.calls.read_text().splitlines()]
        self.assertIn(["compose", "--profile", "models", "--profile", "monitoring", "config", "--quiet"], calls)

    def test_comfyui_data_defaults_to_the_deploying_users_home(self) -> None:
        home = self.root / "operator"
        result = self.run_script("deploy.sh", HOME=str(home))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(f"COMFYUI_DATA_PATH={home}/.local/share/comfyui\n", (self.spark / ".env").read_text())

    def test_selected_deploy_rejects_inactive_gpu_workloads_before_starting(self) -> None:
        for mode, service in (("comfyui", "llm"), ("models", "comfyui"), ("models", "flash"),
                              ("flash", "llm"), ("flash", "embedding"), ("flash", "reranker")):
            with self.subTest(mode=mode, service=service):
                result = self.deploy(mode, service)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(f"Service is not enabled in {mode} mode: {service}", result.stderr)
        for call in map(json.loads, self.calls.read_text().splitlines()):
            self.assertFalse({"up", "pull", "build", "run", "stop"}.intersection(call), call)

    def test_selected_deploy_validates_active_workloads(self) -> None:
        for mode, service in (("comfyui", "comfyui"), ("models", "llm"), ("models", "reranker"), ("flash", "flash")):
            with self.subTest(mode=mode, service=service):
                result = self.deploy(mode, service)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn("DGX Spark configuration is valid", result.stdout)

    def test_unknown_service_is_rejected(self) -> None:
        result = self.deploy("comfyui", "missing")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Service is not enabled", result.stderr)

    def add_model(self, name: str = "decision") -> None:
        self.services[name] = {
            "profiles": ["models"], "image": "example/decision:v1",
            "healthcheck": {"test": ["CMD", "curl", "-f", "http://localhost:9000/ready"]},
            "labels": {"io.dockpad.metrics-port": "9000", "io.dockpad.metrics-job": "decision"},
            "ports": [{"host_ip": "127.0.0.1", "target": 9000, "published": "8003"}],
        }
        self.config.write_text(json.dumps({"services": self.services}))

    def run_script(self, name: str, *args: str, **overrides: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [str(self.spark / "scripts" / name), *args],
            env={**self.env, **overrides}, capture_output=True, text=True, timeout=20,
        )

    def test_missing_mode_defaults_to_models_and_preserves_additional_settings(self) -> None:
        (self.spark / ".env").write_text("DECISION_MODEL=example/future\n# local setting\n")
        result = self.run_script("deploy.sh")
        self.assertEqual(result.returncode, 0, result.stderr)
        settings = (self.spark / ".env").read_text()
        self.assertIn("SPARK_MODE=models\n", settings)
        self.assertIn("DECISION_MODEL=example/future\n# local setting\n", settings)
        calls = [json.loads(line) for line in self.calls.read_text().splitlines()]
        self.assertIn(["compose", "--profile", "models", "config", "--quiet"], calls)

    def test_fresh_deployment_defaults_to_models(self) -> None:
        result = self.run_script("deploy.sh", DRY_RUN="false", SKIP_PULL="false")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("SPARK_MODE=models", (self.spark / ".env").read_text())
        calls = [json.loads(line) for line in self.calls.read_text().splitlines()]
        self.assertEqual(sum("run" in call for call in calls), 3)
        self.assertFalse(any("build" in call for call in calls))
        self.assertEqual(calls[-1], ["compose", "--profile", "models", "up", "-d"])

    def test_model_without_healthcheck_is_rejected_before_starting(self) -> None:
        self.add_model()
        del self.services["decision"]["healthcheck"]
        self.config.write_text(json.dumps({"services": self.services}))
        result = self.deploy("models", "decision", DRY_RUN="false")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("decision: model services require a Compose healthcheck", result.stderr)
        calls = [json.loads(line) for line in self.calls.read_text().splitlines()]
        self.assertFalse(any("stop" in call or "up" in call for call in calls))

    def test_reselecting_models_does_not_stop_the_running_models(self) -> None:
        (self.spark / ".env").write_text("SPARK_MODE=models\n")
        result = self.run_script("switch-mode.sh", "models", DRY_RUN="false", HEALTH_WAIT_SECONDS="0")
        self.assertEqual(result.returncode, 0, result.stderr)
        calls = [json.loads(line) for line in self.calls.read_text().splitlines()]
        stops = [call for call in calls if "stop" in call]
        self.assertEqual(stops, [
            ["compose", "--profile", "comfyui", "stop", "comfyui"],
            ["compose", "--profile", "flash", "stop", "flash"],
        ])

    def test_additional_runtime_is_deployed_and_discovered_without_hf_download(self) -> None:
        self.add_model()
        result = self.deploy("models", "decision", DRY_RUN="false")
        self.assertEqual(result.returncode, 0, result.stderr)
        calls = [json.loads(line) for line in self.calls.read_text().splitlines()]
        self.assertFalse(any("run" in call for call in calls))
        self.assertEqual(calls[-1], ["compose", "--profile", "models", "up", "-d", "decision"])
        targets = json.loads((self.spark / "grafana/model-targets.json").read_text())
        self.assertEqual(targets[-1], {
            "targets": ["decision:9000"],
            "labels": {"service": "decision", "job": "decision", "__metrics_path__": "/metrics"},
        })

    def test_selected_model_prepares_dependency_snapshots(self) -> None:
        result = self.deploy("models", "reranker", DRY_RUN="false", SKIP_PULL="false")
        self.assertEqual(result.returncode, 0, result.stderr)
        calls = [json.loads(line) for line in self.calls.read_text().splitlines()]
        snapshots = [call for call in calls if "run" in call]
        self.assertEqual([call[-1] for call in snapshots], ["example/llm", "example/embedding", "example/reranker"])
        for call in snapshots:
            self.assertIn("--no-deps", call)
            self.assertIn("HF_HUB_OFFLINE=0", call)

    def test_additional_model_health_and_metrics_are_checked(self) -> None:
        self.add_model()
        (self.spark / ".env").write_text("SPARK_MODE=models\n")
        result = self.run_script("health-check.sh", HEALTH_WAIT_SECONDS="0", TEST_FAIL_HEALTH="decision")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("FAIL dgx-spark/decision", result.stderr)
        self.assertIn("http://127.0.0.1:8003/metrics", self.http_calls.read_text())

    def test_switch_stops_every_model_including_additional_runtime(self) -> None:
        self.add_model()
        (self.spark / ".env").write_text(f"SPARK_MODE=models\nCOMFYUI_DATA_PATH={self.root}/data\n")
        result = self.run_script("switch-mode.sh", "comfyui", DRY_RUN="false", HEALTH_WAIT_SECONDS="0")
        self.assertEqual(result.returncode, 0, result.stderr)
        calls = [json.loads(line) for line in self.calls.read_text().splitlines()]
        stop = next(call for call in calls if "stop" in call)
        self.assertEqual(stop[stop.index("stop") + 1:], ["llm", "embedding", "reranker", "decision"])
        self.assertLess(next(i for i, call in enumerate(calls) if "build" in call), calls.index(stop))
        self.assertIn("SPARK_MODE=comfyui", (self.spark / ".env").read_text())

    def test_prepare_failure_keeps_current_mode_running(self) -> None:
        (self.spark / ".env").write_text(f"SPARK_MODE=models\nCOMFYUI_DATA_PATH={self.root}/data\n")
        result = self.run_script("switch-mode.sh", "comfyui", DRY_RUN="false", TEST_FAIL_BUILD="true")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("SPARK_MODE=models", (self.spark / ".env").read_text())
        calls = [json.loads(line) for line in self.calls.read_text().splitlines()]
        self.assertFalse(any("stop" in call or "up" in call for call in calls))

    def test_failed_switch_restores_every_model(self) -> None:
        self.add_model()
        (self.spark / ".env").write_text(f"SPARK_MODE=models\nCOMFYUI_DATA_PATH={self.root}/data\n")
        result = self.run_script("switch-mode.sh", "comfyui", DRY_RUN="false", HEALTH_WAIT_SECONDS="0", TEST_FAIL_HEALTH="comfyui")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("restoring models", result.stderr)
        self.assertIn("SPARK_MODE=models", (self.spark / ".env").read_text())
        calls = [json.loads(line) for line in self.calls.read_text().splitlines()]
        self.assertIn(["compose", "--profile", "models", "up", "-d"], calls)
        self.assertIn("OK   dgx-spark/decision", result.stdout)

    def test_build_and_model_download_follow_the_selected_mode(self) -> None:
        for mode, service, other in (("comfyui", "comfyui", "models"), ("models", "llm", "comfyui"),
                                    ("flash", "flash", "models")):
            with self.subTest(mode=mode):
                self.calls.unlink(missing_ok=True)
                result = self.deploy(mode, service, DRY_RUN="false", SKIP_PULL="false", COMPOSE_PROFILES=other)
                self.assertEqual(result.returncode, 0, result.stderr)
                calls = [json.loads(line) for line in self.calls.read_text().splitlines()]
                self.assertEqual(sum("build" in call for call in calls), int(mode in {"comfyui", "flash"}))
                self.assertEqual(sum("run" in call for call in calls), {"comfyui": 0, "models": 1, "flash": 2}[mode])
                self.assertEqual(calls[-1], ["compose", "--profile", mode, "up", "-d", service])

    def test_health_checks_only_the_selected_workload_mode(self) -> None:
        for mode, other in (("comfyui", "models"), ("models", "comfyui"), ("flash", "models")):
            with self.subTest(mode=mode):
                self.http_calls.unlink(missing_ok=True)
                (self.spark / ".env").write_text(f"SPARK_MODE={mode}\n")
                result = subprocess.run(
                    [str(self.spark / "scripts/health-check.sh")],
                    env={**self.env, "COMPOSE_PROFILES": other, "HEALTH_WAIT_SECONDS": "0"},
                    capture_output=True, text=True, timeout=10,
                )
                self.assertEqual(result.returncode, 0, result.stderr)
                urls = self.http_calls.read_text().splitlines()
                expected = ["http://127.0.0.1:8188/system_stats"] if mode == "comfyui" else [
                    f"http://127.0.0.1:{port}/{path}"
                    for port in ((8000,) if mode == "flash" else (8000, 8001, 8002)) for path in ("metrics",)
                ]
                self.assertEqual(urls, expected)

    def test_flash_switch_and_return_preserve_models_and_select_metrics(self) -> None:
        self.add_model()
        original = "LLM_MODEL=example/original\nLLM_MAX_MODEL_LEN=131072\nVLLM_IMAGE=example/vllm:v1\n"
        (self.spark / ".env").write_text("SPARK_MODE=models\n" + original)
        for target in ("flash", "models"):
            with self.subTest(target=target):
                self.calls.unlink(missing_ok=True)
                result = self.run_script("switch-mode.sh", target, DRY_RUN="false", HEALTH_WAIT_SECONDS="0")
                self.assertEqual(result.returncode, 0, result.stderr)
                settings = (self.spark / ".env").read_text()
                self.assertIn(original, settings)
                self.assertIn(f"SPARK_MODE={target}\n", settings)
                calls = [json.loads(line) for line in self.calls.read_text().splitlines()]
                snapshots = [call[-1] for call in calls if "run" in call and "-c" in call]
                self.assertEqual(snapshots, ["example/flash"] if target == "flash" else
                                 ["example/llm", "example/embedding", "example/reranker"])
                stop_calls = [call for call in calls if "stop" in call]
                for call in stop_calls:
                    self.assertNotEqual(call[call.index("--profile") + 1], target)
                last_download = max(i for i, call in enumerate(calls) if "run" in call)
                first_stop = min(i for i, call in enumerate(calls) if "stop" in call)
                self.assertLess(last_download, first_stop)
                self.assertEqual(calls[first_stop][calls[first_stop].index("stop") + 1:],
                                 ["llm", "embedding", "reranker", "decision"] if target == "flash" else ["comfyui"])
                targets = json.loads((self.spark / "grafana/model-targets.json").read_text())
                self.assertEqual([item["labels"]["service"] for item in targets],
                                 ["flash"] if target == "flash" else ["llm", "embedding", "reranker", "decision"])
                if target == "flash":
                    self.assertEqual(targets[0]["labels"]["job"], "vllm")

    def test_flash_download_failure_keeps_models_running(self) -> None:
        (self.spark / ".env").write_text("SPARK_MODE=models\n")
        result = self.run_script("switch-mode.sh", "flash", DRY_RUN="false", TEST_FAIL_DOWNLOAD="true")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("SPARK_MODE=models", (self.spark / ".env").read_text())
        calls = [json.loads(line) for line in self.calls.read_text().splitlines()]
        self.assertFalse(any("stop" in call or "up" in call for call in calls))

    def test_failed_flash_switch_restores_models_and_metrics(self) -> None:
        (self.spark / ".env").write_text("SPARK_MODE=models\n")
        result = self.run_script("switch-mode.sh", "flash", DRY_RUN="false", HEALTH_WAIT_SECONDS="0", TEST_FAIL_HEALTH="flash")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("restoring models", result.stderr)
        self.assertIn("SPARK_MODE=models", (self.spark / ".env").read_text())
        calls = [json.loads(line) for line in self.calls.read_text().splitlines()]
        self.assertIn(["compose", "--profile", "flash", "stop", "flash"], calls)
        self.assertIn(["compose", "--profile", "models", "up", "-d"], calls)
        targets = json.loads((self.spark / "grafana/model-targets.json").read_text())
        self.assertEqual([item["labels"]["service"] for item in targets], ["llm", "embedding", "reranker"])

    def test_comfyui_clears_model_metrics_targets(self) -> None:
        result = self.deploy("comfyui", "comfyui", DRY_RUN="false")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads((self.spark / "grafana/model-targets.json").read_text()), [])
        self.assertEqual(json.loads((self.spark / "api/model-targets.json").read_text()), [])

    def test_catalog_membership_follows_profiles_and_opt_in_api_labels(self) -> None:
        self.add_model()
        self.services["decision"]["labels"]["io.dockpad.api-kind"] = "chat"
        self.config.write_text(json.dumps({"services": self.services}))
        result = self.deploy("models", "llm", DRY_RUN="false")
        self.assertEqual(result.returncode, 0, result.stderr)
        targets = json.loads((self.spark / "api/model-targets.json").read_text())
        self.assertEqual([target["service"] for target in targets], ["llm", "embedding", "reranker", "decision"])
        self.assertEqual(targets[-1]["url"], "http://decision:9000/v1/models")
        result = self.deploy("flash", "flash", DRY_RUN="false")
        self.assertEqual(result.returncode, 0, result.stderr)
        targets = json.loads((self.spark / "api/model-targets.json").read_text())
        self.assertEqual(targets, [{"service": "flash", "url": "http://flash:8000/v1/models", "kind": "chat"}])

    def test_flash_context_must_fit_the_bounded_pool(self) -> None:
        (self.spark / ".env").write_text("SPARK_MODE=flash\nFLASH_MAX_MODEL_LEN=262145\n")
        result = self.run_script("deploy.sh", DRY_RUN="false")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("FLASH_MAX_MODEL_LEN must be between", result.stderr)
        calls = [json.loads(line) for line in self.calls.read_text().splitlines()]
        self.assertFalse(any("stop" in call or "up" in call for call in calls))

    def test_flash_prepares_pinned_snapshot_and_runtime_before_stopping_other_modes(self) -> None:
        revision = "a" * 40
        self.services["flash"]["labels"]["io.dockpad.hf-revision"] = revision
        self.config.write_text(json.dumps({"services": self.services}))
        result = self.deploy("flash", "flash", DRY_RUN="false")
        self.assertEqual(result.returncode, 0, result.stderr)
        calls = [json.loads(line) for line in self.calls.read_text().splitlines()]
        download = next(call for call in calls if "-c" in call)
        self.assertEqual(download[-2:], ["example/flash", revision])
        prepare = next(call for call in calls if "--prepare-only" in call)
        build = next(call for call in calls if "build" in call)
        first_stop = next(i for i, call in enumerate(calls) if "stop" in call)
        self.assertLess(calls.index(build), calls.index(download))
        self.assertLess(calls.index(download), calls.index(prepare))
        self.assertLess(calls.index(prepare), first_stop)

    def test_flash_build_failure_does_not_stop_current_mode(self) -> None:
        (self.spark / ".env").write_text("SPARK_MODE=models\n")
        result = self.run_script("switch-mode.sh", "flash", DRY_RUN="false", TEST_FAIL_BUILD="true")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("SPARK_MODE=models", (self.spark / ".env").read_text())
        calls = [json.loads(line) for line in self.calls.read_text().splitlines()]
        self.assertFalse(any("stop" in call or "up" in call for call in calls))

    def test_service_list_includes_stopped_containers(self) -> None:
        (self.spark / ".env").write_text("SPARK_MODE=comfyui\n")
        result = subprocess.run(
            [str(self.spark / "scripts/compose.sh"), "ps-json"], env=self.env,
            capture_output=True, text=True, timeout=10,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        calls = [json.loads(line) for line in self.calls.read_text().splitlines()]
        self.assertEqual(calls, [["compose", "--profile", "comfyui", "ps", "--all", "--format", "json"]])
