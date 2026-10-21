#!/usr/bin/env python3
"""Read workload membership and model metadata from the rendered Compose config."""

import argparse
import json
import os
import re
import subprocess
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PREFIX = "io.dockpad."
MODES = ("models", "flash", "comfyui")
MODEL_MODES = {"models", "flash"}
API_KINDS = {"chat", "embedding", "reranker"}


def load_services() -> dict:
    result = subprocess.run(
        ["docker", "compose", "--profile", "*", "config", "--no-env-resolution", "--format", "json"],
        cwd=ROOT, check=True, text=True, capture_output=True,
    )
    services = json.loads(result.stdout)["services"]
    for name, service in services.items():
        profiles = set(service.get("profiles", []))
        if len(set(MODES) & profiles) > 1:
            raise ValueError(f"{name}: workload profiles must be exclusive")
        if not MODEL_MODES.intersection(profiles):
            continue
        if not re.fullmatch(r"[a-z0-9][a-z0-9-]*", name):
            raise ValueError(f"invalid model service name: {name}")
        health = service.get("healthcheck", {})
        if health.get("disable") or not health.get("test") or health["test"][0] == "NONE":
            raise ValueError(f"{name}: model services require a Compose healthcheck")
        labels = service.get("labels", {})
        model = labels.get(PREFIX + "hf-model")
        if model and not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", model):
            raise ValueError(f"{name}: invalid Hugging Face model ID")
        revision = labels.get(PREFIX + "hf-revision")
        if revision and not re.fullmatch(r"[a-f0-9]{40}", revision):
            raise ValueError(f"{name}: Hugging Face revision requires a full commit SHA")
        if PREFIX + "metrics-port" in labels:
            metrics_endpoint(name, service)
        if PREFIX + "api-kind" in labels:
            if labels[PREFIX + "api-kind"] not in API_KINDS:
                raise ValueError(f"{name}: invalid API kind")
            if PREFIX + "metrics-port" not in labels:
                raise ValueError(f"{name}: API catalog requires a metrics port shared with the model API")
    return services


def mode_services(services: dict, mode: str) -> dict:
    return {name: service for name, service in services.items() if mode in service.get("profiles", [])}


def selected_services(services: dict, selected: str | None) -> set[str]:
    if not selected:
        return set(services)
    if selected not in services:
        raise ValueError(f"unknown service: {selected}")
    included: set[str] = set()

    def include(name: str) -> None:
        if name in included:
            return
        included.add(name)
        for dependency in services[name].get("depends_on", {}):
            include(dependency)

    include(selected)
    return included


def metrics_endpoint(name: str, service: dict) -> tuple[int, int, str, str]:
    labels = service.get("labels", {})
    port = int(labels[PREFIX + "metrics-port"])
    job = labels.get(PREFIX + "metrics-job", "vllm")
    path = labels.get(PREFIX + "metrics-path", "/metrics")
    if not 1 <= port <= 65535 or not re.fullmatch(r"[a-zA-Z0-9_-]+", job):
        raise ValueError(f"{name}: invalid metrics port or job")
    if not re.fullmatch(r"/[a-zA-Z0-9_./-]+", path):
        raise ValueError(f"{name}: invalid metrics path")
    for binding in service.get("ports", []):
        if binding.get("host_ip") == "127.0.0.1" and binding["target"] == port:
            return port, int(binding["published"]), job, path
    raise ValueError(f"{name}: metrics port {port} requires a loopback port binding")


def metrics_targets(services: dict, mode: str) -> list[dict]:
    targets = []
    for name, service in mode_services(services, mode).items():
        if PREFIX + "metrics-port" not in service.get("labels", {}):
            continue
        port, _, job, path = metrics_endpoint(name, service)
        targets.append({"targets": [f"{name}:{port}"], "labels": {
            "service": name, "job": job, "__metrics_path__": path,
        }})
    return targets


def api_targets(services: dict, mode: str) -> list[dict]:
    targets = []
    for name, service in mode_services(services, mode).items():
        kind = service.get("labels", {}).get(PREFIX + "api-kind")
        if kind is None:
            continue
        port, _, _, _ = metrics_endpoint(name, service)
        targets.append({"service": name, "url": f"http://{name}:{port}/v1/models", "kind": kind})
    return targets


def write_json(destination: Path, data: list[dict]) -> None:
    content = json.dumps(data, indent=2) + "\n"
    if destination.exists() and destination.read_text() == content:
        return
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", dir=destination.parent, delete=False) as output:
        output.write(content)
        temporary = Path(output.name)
    temporary.chmod(0o644)
    temporary.replace(destination)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="action", required=True)
    commands.add_parser("list").add_argument("mode", choices=MODES)
    snapshots = commands.add_parser("snapshots")
    snapshots.add_argument("service", nargs="?")
    snapshots.add_argument("--mode", choices=MODES, default=os.environ.get("SPARK_MODE", "models"))
    commands.add_parser("probes").add_argument("mode", choices=MODES)
    commands.add_parser("write-targets").add_argument("mode", choices=MODES)
    args = parser.parse_args()
    services = load_services()
    if args.action == "list":
        for name in mode_services(services, args.mode):
            print(name)
    elif args.action == "snapshots":
        selected = selected_services(services, args.service)
        for name, service in mode_services(services, args.mode).items():
            model = service.get("labels", {}).get(PREFIX + "hf-model")
            if name in selected and model:
                revision = service.get("labels", {}).get(PREFIX + "hf-revision", "")
                print(f"{name}\t{model}\t{revision}")
    elif args.action == "probes":
        for name, service in mode_services(services, args.mode).items():
            if PREFIX + "metrics-port" in service.get("labels", {}):
                _, port, _, path = metrics_endpoint(name, service)
                print(f"{name}\thttp://127.0.0.1:{port}{path}")
    else:
        write_json(ROOT / "grafana" / "model-targets.json", metrics_targets(services, args.mode))
        write_json(ROOT / "api" / "model-targets.json", api_targets(services, args.mode))


if __name__ == "__main__":
    try:
        main()
    except subprocess.CalledProcessError as error:
        raise SystemExit(f"Compose service configuration: {error.stderr.strip() or error}") from error
    except (ValueError, OSError) as error:
        raise SystemExit(f"Compose service configuration: {error}") from error
