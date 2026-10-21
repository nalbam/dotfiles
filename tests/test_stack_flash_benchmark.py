import importlib.util
import json
import unittest
from pathlib import Path
from unittest.mock import patch


SCRIPT = Path(__file__).resolve().parents[1] / "stacks/dgx-spark/bench/benchmark-flash.py"
spec = importlib.util.spec_from_file_location("flash_benchmark", SCRIPT)
benchmark = importlib.util.module_from_spec(spec)
spec.loader.exec_module(benchmark)


class Response:
    def __init__(self, payloads):
        self.lines = [b"data: " + json.dumps(payload).encode() + b"\n\n" for payload in payloads]
        self.lines.append(b"data: [DONE]\n\n")

    def __enter__(self):
        return iter(self.lines)

    def __exit__(self, *args):
        return False


class FlashBenchmarkTests(unittest.TestCase):
    def test_token_rate_uses_usage_instead_of_stream_message_count(self) -> None:
        response = Response([
            {"choices": [{"delta": {"role": "assistant", "content": ""}}]},
            {"choices": [{"delta": {"content": "first content"}}]},
            {"choices": [{"delta": {"content": "second content"}}]},
            {"choices": [], "usage": {"prompt_tokens": 44, "completion_tokens": 320}},
        ])
        with patch.object(benchmark.urllib.request, "urlopen", return_value=response), \
                patch.object(benchmark.time, "perf_counter", side_effect=[100, 102, 112]):
            result = benchmark.sample("http://example/v1", "model", "prompt", 512, {})
        self.assertEqual(result["completion_tokens"], 320)
        self.assertEqual(result["decode_tok_s"], 32)
        self.assertEqual(result["ttft_s"], 2)

    def test_missing_usage_cannot_produce_a_token_rate(self) -> None:
        response = Response([{"choices": [{"delta": {"content": "answer"}}]}])
        with patch.object(benchmark.urllib.request, "urlopen", return_value=response), \
                patch.object(benchmark.time, "perf_counter", side_effect=[100, 102, 112]), \
                self.assertRaisesRegex(ValueError, "completion-token usage"):
            benchmark.sample("http://example/v1", "model", "prompt", 512, {})

    def test_aggregate_rate_includes_batch_latency(self) -> None:
        requests = [
            {"started": 100, "ended": 112, "completion_tokens": 120, "decode_tok_s": 12, "ttft_s": 2},
            {"started": 101, "ended": 115, "completion_tokens": 150, "decode_tok_s": 15, "ttft_s": 4},
        ]
        with patch.object(benchmark, "sample", side_effect=requests), \
                patch.object(benchmark, "host_memory", return_value=None):
            result = benchmark.measure_batch("http://example/v1", "model", "prompt", 512, {}, 2)
        self.assertEqual(result["aggregate_tok_s"], 18)
        self.assertEqual(result["median_decode_tok_s"], 13.5)
        self.assertEqual(result["median_ttft_s"], 3)
