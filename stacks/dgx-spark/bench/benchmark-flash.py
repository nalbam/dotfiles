#!/usr/bin/env python3
"""Measure streamed model throughput using API token counts, with warmup and repeats."""

import argparse
import concurrent.futures
import json
import os
import statistics
import threading
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path


PROMPTS = {
    "code": "Write a Python function that performs a stable topological sort of a directed graph, detects cycles, and includes a concise usage example. Explain the complexity briefly.",
    "korean": "한국어로 Docker 컨테이너의 healthcheck, restart policy, readiness 차이를 구체적인 서버 운영 사례로 설명해 주세요. 약 20문장으로 작성해 주세요.",
    "prose": "Explain how a city can make its streets safer for pedestrians. Write a detailed, coherent answer covering street design, public transport, speed management, and practical tradeoffs, with concrete examples.",
}


def host_memory() -> dict | None:
    path = Path("/proc/meminfo")
    if not path.is_file():
        return None
    return {line.split()[0].rstrip(":"): int(line.split()[1]) // 1024
            for line in path.read_text().splitlines()
            if line.startswith(("MemAvailable:", "MemFree:", "SwapFree:"))}


def sample(url: str, model: str, prompt: str, tokens: int, headers: dict,
           barrier: threading.Barrier | None = None) -> dict:
    body = {"model": model, "messages": [{"role": "user", "content": prompt}],
            "temperature": 0, "max_tokens": tokens,
            "chat_template_kwargs": {"enable_thinking": False},
            "stream": True, "stream_options": {"include_usage": True}}
    request = urllib.request.Request(url + "/chat/completions", data=json.dumps(body).encode(), headers=headers)
    if barrier is not None:
        barrier.wait(timeout=10)
    started = time.perf_counter()
    first = None
    usage = None
    answer = []
    finish_reason = None
    with urllib.request.urlopen(request, timeout=180) as response:
        for raw in response:
            line = raw.decode().strip()
            if not line.startswith("data: ") or line == "data: [DONE]":
                continue
            data = json.loads(line[6:])
            if data.get("usage"):
                usage = data["usage"]
            for choice in data.get("choices", []):
                content = choice.get("delta", {}).get("content")
                if content:
                    if first is None:
                        first = time.perf_counter()
                    answer.append(content)
                if choice.get("finish_reason"):
                    finish_reason = choice["finish_reason"]
    ended = time.perf_counter()
    if first is None or not usage or usage.get("completion_tokens", 0) <= 0:
        raise ValueError("The endpoint must return content and streamed completion-token usage")
    return {"started": started, "ended": ended, "first_content": first,
            "prompt_tokens": usage["prompt_tokens"], "completion_tokens": usage["completion_tokens"],
            "ttft_s": first - started, "decode_tok_s": usage["completion_tokens"] / (ended - first),
            "total_s": ended - started, "finish_reason": finish_reason, "answer": "".join(answer)}


def measure_batch(url: str, model: str, prompt: str, tokens: int, headers: dict, concurrency: int) -> dict:
    barrier = threading.Barrier(concurrency)
    with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency) as executor:
        futures = [executor.submit(sample, url, model, prompt, tokens, headers, barrier)
                   for _ in range(concurrency)]
        requests = [future.result() for future in futures]
    elapsed = max(r["ended"] for r in requests) - min(r["started"] for r in requests)
    return {"concurrency": concurrency, "requests": requests,
            "aggregate_tok_s": sum(r["completion_tokens"] for r in requests) / elapsed,
            "median_decode_tok_s": statistics.median(r["decode_tok_s"] for r in requests),
            "median_ttft_s": statistics.median(r["ttft_s"] for r in requests), "elapsed_s": elapsed,
            "memory_mib": host_memory()}


def save(path: Path, report: dict) -> None:
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    temporary.replace(path)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:8000/v1")
    parser.add_argument("--model", default="qwen3.8-flash-next")
    parser.add_argument("--tokens", type=int, default=512)
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--concurrency", type=int, nargs="+", default=[1, 2, 4])
    parser.add_argument("--workloads", choices=tuple(PROMPTS), nargs="+", default=list(PROMPTS))
    parser.add_argument("--api-key-env", help="Environment variable holding the API key")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.tokens <= 0 or args.repeats <= 0 or any(c <= 0 for c in args.concurrency):
        parser.error("tokens, repeats and concurrency must be positive")
    headers = {"Content-Type": "application/json"}
    if args.api_key_env:
        headers["Authorization"] = "Bearer " + os.environ[args.api_key_env]
    url = args.base_url.rstrip("/")
    report = {"measured_at": datetime.now(timezone.utc).isoformat(), "base_url": url, "model": args.model,
              "temperature": 0, "thinking": False, "max_output_tokens": args.tokens,
              "repeats": args.repeats, "warmup_tokens": 64,
              "definitions": {"token_count": "response.usage.completion_tokens",
                              "decode_tok_s": "completion_tokens / (request_end - first_content)",
                              "aggregate_tok_s": "sum(completion_tokens) / batch_elapsed_including_ttft"},
              "initial_memory_mib": host_memory(), "batches": [], "summary": []}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    for workload in args.workloads:
        for concurrency in args.concurrency:
            measure_batch(url, args.model, PROMPTS[workload], 64, headers, concurrency)
            batches = []
            for repetition in range(args.repeats):
                batch = measure_batch(url, args.model, PROMPTS[workload], args.tokens, headers, concurrency)
                batch.update(workload=workload, repetition=repetition + 1)
                batches.append(batch)
                report["batches"].append(batch)
                save(args.output, report)
                print(json.dumps({"workload": workload, "concurrency": concurrency, "repetition": repetition + 1,
                                  "per_request_tok_s": round(batch["median_decode_tok_s"], 2),
                                  "aggregate_tok_s": round(batch["aggregate_tok_s"], 2),
                                  "ttft_s": round(batch["median_ttft_s"], 3)}), flush=True)
            summary = {"workload": workload, "concurrency": concurrency,
                       "per_request_tok_s": statistics.median(b["median_decode_tok_s"] for b in batches),
                       "aggregate_tok_s": statistics.median(b["aggregate_tok_s"] for b in batches),
                       "ttft_s": statistics.median(b["median_ttft_s"] for b in batches),
                       "completion_tokens": sum(r["completion_tokens"] for b in batches for r in b["requests"])}
            report["summary"].append(summary)
            save(args.output, report)
    print(json.dumps({"summary": report["summary"], "output": str(args.output)}, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
