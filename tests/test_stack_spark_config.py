import json
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPARK = ROOT / "stacks" / "dgx-spark"


def env_values(path: Path) -> dict[str, str]:
    return dict(
        line.split("=", 1)
        for line in path.read_text().splitlines()
        if line and not line.startswith("#")
    )


class SparkConfigTests(unittest.TestCase):
    def test_public_sources_contain_no_account_identifiers(self) -> None:
        config = (SPARK / "grafana" / "config.alloy").read_text()
        for key in ("GCLOUD_FM_URL", "GCLOUD_FM_USERNAME", "GCLOUD_PROM_URL", "GCLOUD_PROM_USERNAME"):
            self.assertIn(f'sys.env("{key}")', config)
        self.assertNotRegex(config, r'username\s*=\s*"[0-9]+"')
        self.assertNotRegex(config, r'url\s*=\s*"https://')
        compose = (SPARK / "docker-compose.yml").read_text()
        self.assertIn("${COMFYUI_DATA_PATH:?COMFYUI_DATA_PATH is required}", compose)
        self.assertNotIn("/home/", compose)
        self.assertNotIn("COMFYUI_DATA_PATH", env_values(SPARK / ".env.example"))
        self.assertIn('COMFYUI_DATA_PATH="${COMFYUI_DATA_PATH:-$HOME/.local/share/comfyui}"',
                      (SPARK / "scripts" / "deploy.sh").read_text())
        vibemon = env_values(SPARK / "vibemon.env")
        self.assertNotIn("VIBEMON_SOURCE_ID", vibemon)
        self.assertNotIn("VIBEMON_SOURCE_NAME", vibemon)

    def test_dashboard_covers_host_gpu_workloads_and_io(self) -> None:
        dashboard = json.loads(
            (ROOT / "stacks" / "grafana" / "dashboards" / "dgx-spark.json").read_text()
        )
        panel_ids = [panel["id"] for panel in dashboard["panels"]]
        queries = "\n".join(
            target["expr"]
            for panel in dashboard["panels"]
            for target in panel.get("targets", [])
        )

        self.assertEqual(dashboard["uid"], "dgx-spark")
        self.assertEqual(dashboard["refresh"], "10s")
        self.assertEqual(len(panel_ids), len(set(panel_ids)))
        for metric in (
            "node_cpu_seconds_total",
            "DCGM_FI_DEV_GPU_UTIL",
            "vllm:num_requests_running",
            "vllm:num_requests_waiting",
            "vllm:kv_cache_usage_perc",
            "vllm:prefix_cache_hits_total",
            "vllm:spec_decode_num_accepted_tokens_total",
            "vllm:spec_decode_num_draft_tokens_total",
            "probe_success",
            "node_network_receive_bytes_total",
            "node_disk_written_bytes_total",
        ):
            self.assertIn(metric, queries)

    def test_comfyui_uses_versioned_arm64_cuda_image(self) -> None:
        environment = env_values(SPARK / ".env.example")
        compose = (SPARK / "docker-compose.yml").read_text()
        dockerfile = (SPARK / "Dockerfile.comfyui").read_text()

        self.assertRegex(environment["COMFYUI_VERSION"], r"^v[0-9]+\.[0-9]+\.[0-9]+$")
        self.assertRegex(environment["NGC_PYTORCH_IMAGE"], r"^nvcr\.io/nvidia/pytorch:[0-9]+\.[0-9]+-py3$")
        self.assertIn("FROM ${NGC_PYTORCH_IMAGE}", dockerfile)
        self.assertIn('git clone --branch "${COMFYUI_VERSION}"', dockerfile)
        self.assertIn("127.0.0.1:8188:8188", compose)
        self.assertIn("${TAILSCALE_IP:?TAILSCALE_IP is required}:8188:8188", compose)
        self.assertIn("/opt/ComfyUI/models", compose)
        self.assertIn("/opt/ComfyUI/output", compose)
        self.assertIn("profiles: [comfyui]", compose)
        self.assertIn("ngc-stub", dockerfile)
        self.assertIn("torchaudio/functional.py", dockerfile)
        self.assertIn("torchaudio/transforms.py", dockerfile)

    def test_models_are_versioned_and_selected_by_default(self) -> None:
        environment = env_values(SPARK / ".env.example")
        compose = (SPARK / "docker-compose.yml").read_text()

        self.assertEqual(environment["SPARK_MODE"], "models")
        self.assertRegex(environment["VLLM_IMAGE"], r":v[0-9]+\.[0-9]+\.[0-9]+$")
        self.assertIn("Qwen3.6", environment["LLM_MODEL"])
        self.assertIn("Qwen3-", environment["EMBEDDING_MODEL"])
        self.assertIn("Qwen3-", environment["RERANKER_MODEL"])
        for key in ("LLM_REVISION", "EMBEDDING_REVISION", "RERANKER_REVISION"):
            self.assertNotIn(key, environment)
        self.assertNotIn("--revision", compose)
        self.assertNotIn("--tokenizer-revision", compose)
        self.assertIn('HF_HUB_OFFLINE: "1"', compose)
        self.assertIn('TRANSFORMERS_OFFLINE: "1"', compose)
        self.assertEqual(compose.count("profiles: [models]"), 3)
        deployment = (SPARK / "scripts" / "deploy.sh").read_text()
        self.assertNotIn("@sha256:", deployment)

    def test_health_check_verifies_comfyui_cuda_device(self) -> None:
        compose = (SPARK / "docker-compose.yml").read_text()
        health_check = (SPARK / "scripts" / "health-check.sh").read_text()

        self.assertIn("start_period: 2m", compose)
        self.assertIn("http://127.0.0.1:8188/system_stats", health_check)
        self.assertIn('"cuda" in str(device.get("type", "")).lower()', health_check)

    def test_alloy_scrapes_every_spark_metric_source(self) -> None:
        config = (SPARK / "grafana" / "config.alloy").read_text()
        compose = (SPARK / "docker-compose.yml").read_text()

        for component in (
            'prometheus.scrape "comfyui"',
            'prometheus.scrape "node"',
            'prometheus.scrape "dcgm"',
            'prometheus.scrape "vllm"',
        ):
            self.assertIn(component, config)
        self.assertIn('prometheus.exporter.unix "spark"', config)
        self.assertIn('prometheus.exporter.blackbox "comfyui"', config)
        self.assertIn('source_labels = ["mode"]', config)
        self.assertIn('regex         = "models|flash"', config)
        self.assertIn('replacement  = "comfyui"', config)
        self.assertIn('SPARK_MODE: ${SPARK_MODE:-models}', compose)
        self.assertIn('discovery.file "models"', config)
        self.assertIn('targets = discovery.file.models.targets', config)
        self.assertNotIn('prometheus.exporter.cadvisor "spark"', config)
        self.assertIn(
            'disable_collectors = ["ipvs", "btrfs", "infiniband", "xfs", "zfs", "cpufreq"]',
            config,
        )
        self.assertNotIn("quay.io/prometheus/node-exporter", compose)

        health_check = (SPARK / "scripts" / "health-check.sh").read_text()
        setup = (SPARK / "scripts" / "setup-grafana.sh").read_text()
        self.assertIn("prometheus.exporter.unix.spark/metrics", health_check)
        self.assertIn('--output "$metrics_file"', health_check)
        self.assertIn("inactive Alloy target is still configured", health_check)
        self.assertIn('echo "OK   Grafana Cloud remote write"', health_check)
        self.assertIn("source .env.grafana", setup)
        self.assertIn('curl -fsS --output "$metrics_file"', setup)


if __name__ == "__main__":
    unittest.main()
