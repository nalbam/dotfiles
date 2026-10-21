"""Run the pinned TensorFold CUDA recipe within the managed Compose service."""

import argparse
import importlib.util
import json
import os
import re
import subprocess
from pathlib import Path


GIB = 2**30


def draft_vocabulary(snapshot: Path, cache: Path, mode: str) -> Path:
    if mode not in {"multilingual", "english_code"}:
        raise ValueError("FLASH_DRAFT_VOCAB must be multilingual or english_code")
    root = Path(importlib.util.find_spec("tensorfold").origin).parent
    base = root / "families/qwen4_exp/cuda/draft_vocab.txt"
    if mode == "english_code":
        return base
    module_path = Path(__file__).with_name("flash-vocabulary.py")
    spec = importlib.util.spec_from_file_location("flash_vocabulary", module_path)
    vocabulary = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(vocabulary)
    destination = cache / "draft_vocab" / snapshot.parent.parent.name / snapshot.name / "ko_utf8_v1.txt"
    metadata = vocabulary.build_vocabulary(snapshot / "tokenizer.json", base, destination)
    print(json.dumps({"draft_vocabulary": metadata}), flush=True)
    return destination


def memory_info(path: Path = Path("/proc/meminfo")) -> dict[str, int]:
    return {line.split()[0].rstrip(":"): int(line.split()[1]) * 1024
            for line in path.read_text().splitlines() if line.startswith(("MemTotal:", "MemAvailable:"))}


def snapshot_path(cache: Path, model: str, revision: str) -> Path:
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", model) or any(part in {".", ".."} for part in model.split("/")):
        raise ValueError("invalid Flash Hugging Face model ID")
    if not re.fullmatch(r"[a-f0-9]{40}", revision):
        raise ValueError("FLASH_REVISION must be a full Hugging Face commit SHA")
    snapshot = cache / "hub" / ("models--" + model.replace("/", "--")) / "snapshots" / revision
    index = json.loads((snapshot / "model.safetensors.index.json").read_text())
    shards = set(index["weight_map"].values())
    if not shards or any(Path(name).name != name or not (snapshot / name).is_file()
                         or (snapshot / name).stat().st_size == 0 for name in shards):
        raise ValueError(f"Flash snapshot is incomplete: {snapshot}")
    return snapshot


def serve_command(snapshot: Path, context: int, sequences: int, reserve: int,
                  thinking_budget: int = 512) -> list[str]:
    if not 1024 <= context <= 262144 or not 1 <= sequences <= 4:
        raise ValueError("Flash requires 1024..262144 context tokens and 1..4 concurrent sequences")
    if not 8 <= reserve <= 32:
        raise ValueError("Flash requires 8..32 GiB host reserve")
    if not 1 <= thinking_budget <= 8192:
        raise ValueError("Flash requires 1..8192 thinking tokens")
    return [
        "tensorfold", "serve", str(snapshot),
        "--host", "0.0.0.0", "--port", "8000", "--name", "qwen3.8-flash-next",
        "--parallel", str(sequences), "--context", str(context), "--kv-dtype", "int8",
        "--ple-on-ssd", "--vision", "--vision-max-images", "50",
        "--mtp-drafts", "6", "--mtp-confidence", "0.60",
        "--temperature", "1.0", "--top-p", "0.95", "--top-k", "20",
        "--no-thinking", "--thinking-budget", str(thinking_budget), "--max-tokens", "32768",
    ]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prepare-only", action="store_true")
    parser.add_argument("--print-command", action="store_true")
    args = parser.parse_args()
    model = os.environ["FLASH_MODEL"]
    revision = os.environ["FLASH_REVISION"]
    context = int(os.environ.get("FLASH_MAX_MODEL_LEN", "262144"))
    sequences = int(os.environ.get("FLASH_MAX_NUM_SEQS", "4"))
    reserve = int(os.environ.get("FLASH_HOST_RESERVE_GIB", "8"))
    thinking_budget = int(os.environ.get("FLASH_THINKING_BUDGET", "512"))
    vocabulary_mode = os.environ.get("FLASH_DRAFT_VOCAB", "multilingual")
    snapshot = snapshot_path(Path("/root/.cache/huggingface"), model, revision)
    command = serve_command(snapshot, context, sequences, reserve, thinking_budget)
    from tensorfold.cli import build_parser
    build_parser().parse_args(command[1:])
    vocabulary = draft_vocabulary(snapshot, Path("/cache"), vocabulary_mode)
    os.environ["TENSORFOLD_DRAFT_VOCAB_PATH"] = str(vocabulary)
    os.environ["TENSORFOLD_MEMORY_RESERVE_GIB"] = str(reserve)
    if args.prepare_only:
        subprocess.run(["tensorfold", "info", str(snapshot)], check=True)
        return
    if not args.print_command:
        memory = memory_info()
        if memory["MemTotal"] < 121 * GIB:
            raise ValueError("Flash requires the 128 GB Spark pool")
        # TensorFold admits the actual context/cache geometry before loading weights.
        if memory["MemAvailable"] < (86 + reserve) * GIB:
            raise ValueError("Insufficient memory for TensorFold weights and host reserve; stop other GPU workloads")
    print(json.dumps({"model": model, "revision": revision, "engine": "tensorfold",
                      "context": context, "sequences": sequences, "host_reserve_gib": reserve}), flush=True)
    if args.print_command:
        print(json.dumps(command))
        return
    os.execvp(command[0], command)


if __name__ == "__main__":
    main()
