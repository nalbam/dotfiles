#!/usr/bin/env python3
"""Compare prefix reuse at 1..4 concurrent requests with occupied idle slots."""

import argparse
import concurrent.futures
import json
from pathlib import Path
import threading
import time
import urllib.request


def request(base, prefix, suffix, barrier=None):
    body = {"model": "qwen3.8-flash-next", "messages": [
        {"role": "system", "content": prefix}, {"role": "user", "content": "Reply OK. " + suffix}],
        "max_tokens": 1, "temperature": 0, "chat_template_kwargs": {"enable_thinking": False}}
    req = urllib.request.Request(base + "/chat/completions", data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    if barrier is not None:
        barrier.wait(timeout=10)
    started = time.monotonic()
    with urllib.request.urlopen(req, timeout=180) as response:
        data = json.load(response)
    usage = data["usage"]
    return {"elapsed_s": time.monotonic() - started, "prompt_tokens": usage["prompt_tokens"],
            "cached_tokens": usage.get("prompt_tokens_details", {}).get("cached_tokens", 0),
            "completion_tokens": usage["completion_tokens"], "stats": data.get("tensorfold", {})}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:8000/v1")
    parser.add_argument("--repeats", type=int, default=1)
    parser.add_argument("--rows", type=int, default=1200)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.repeats < 1 or args.rows < 1:
        parser.error("repeats and rows must be positive")
    base = args.base_url.rstrip("/")
    # Retained, unrelated prompt states must occupy all slots before the shared
    # prefix arrives; an empty server otherwise hides the idle-slot recycling bug.
    barrier = threading.Barrier(4)
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        warm = [executor.submit(request, base, f"Unrelated prefix {i}. " * 200, "warm", barrier) for i in range(4)]
        for future in warm:
            future.result()
    prefix = "These records are reference text for a cache diagnostic.\n" + "".join(
        f"Cache probe row {i}: cedar maple amber river stone blue green.\n" for i in range(args.rows))
    results = {"cold": request(base, prefix, "seed"), "batches": []}
    for repeat in range(args.repeats):
        for count in (1, 2, 3, 4, 1):
            barrier = threading.Barrier(count)
            with concurrent.futures.ThreadPoolExecutor(max_workers=count) as executor:
                futures = [executor.submit(request, base, prefix, f"repeat{repeat}-batch{count}-item{i}", barrier)
                           for i in range(count)]
                batch = {"repeat": repeat + 1, "concurrency": count, "requests": [f.result() for f in futures]}
            results["batches"].append(batch)
            args.output.write_text(json.dumps(results, indent=2) + "\n")
            print(json.dumps(batch), flush=True)


if __name__ == "__main__":
    main()
