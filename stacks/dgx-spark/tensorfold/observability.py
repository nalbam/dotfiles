"""Bounded request metadata and metrics; never record prompts, answers or headers."""

from collections import Counter
from functools import wraps
import json
import threading
import time
import uuid


BUCKETS = (0.1, 0.25, 0.5, 1, 2.5, 5, 10, 30, 60, 120, 300)
_INIT = threading.Lock()


class Observations:
    def __init__(self):
        self.lock = threading.Lock()
        self.outcomes = Counter()
        self.finishes = Counter()
        self.prompt = self.cached = self.reasoning = self.empty = 0
        self.first_content = [0] * (len(BUCKETS) + 1)
        self.first_content_sum = 0.0

    def record(self, event):
        with self.lock:
            self.outcomes[event["outcome"]] += 1
            if event["finish_reason"] is not None:
                self.finishes[event["finish_reason"]] += 1
                self.prompt += event["prompt_tokens"]
                self.cached += event["cached_tokens"]
                self.reasoning += event["reasoning_tokens"]
                self.empty += not event["answer_chars"] and not event["tool_calls"]
            value = event["first_content_s"]
            if value is not None:
                self.first_content_sum += value
                index = next((i for i, edge in enumerate(BUCKETS) if value <= edge), len(BUCKETS))
                self.first_content[index] += 1


def observations(app):
    with _INIT:
        if not hasattr(app, "dockpad_observations"):
            app.dockpad_observations = Observations()
        return app.dockpad_observations


def observe_request(run):
    @wraps(run)
    def observed(self, body, chat, emit, **kwargs):
        started = time.perf_counter()
        prepared = kwargs.get("prepared")
        event = {"event": "flash_request", "request_id": uuid.uuid4().hex,
                 "stream": bool(body.get("stream")), "thinking": getattr(prepared, "thinking", None),
                 "max_tokens": getattr(prepared, "max_tokens", None),
                 "thinking_budget": getattr(prepared, "think_budget", None),
                 "prompt_tokens": len(prepared.prompt) if prepared is not None else None,
                 "reasoning_chars": 0, "answer_chars": 0, "tool_calls": None,
                 "first_reasoning_s": None, "first_content_s": None, "first_tool_call_s": None,
                 "outcome": "error", "finish_reason": None}
        print(json.dumps({"event": "flash_request_started", **{key: event[key] for key in
                         ("request_id", "stream", "thinking", "thinking_budget", "max_tokens", "prompt_tokens")}},
                         separators=(",", ":")), flush=True)

        def output(delta):
            event["reasoning_chars"] += len(delta.get("reasoning_content") or "")
            event["answer_chars"] += len(delta.get("content") or "")
            for key, field in (("reasoning_content", "first_reasoning_s"),
                               ("content", "first_content_s"), ("tool_calls", "first_tool_call_s")):
                if delta.get(key) and event[field] is None:
                    event[field] = round(time.perf_counter() - started, 6)
            return emit(delta)

        try:
            result = run(self, body, chat, output, **kwargs)
            finish = result["finish"]
            event.update(outcome="truncated" if finish == "length" else "completed", finish_reason=finish,
                         prompt_tokens=result["prompt_tokens"], cached_tokens=result["cached_tokens"],
                         completion_tokens=result["completion_tokens"], reasoning_tokens=result["reasoning_tokens"],
                         answer_chars=len(result["content"] or ""), tool_calls=len(result["calls"] or []),
                         prefill_s=result["stats"].get("prefill_s"), decode_s=result["stats"].get("decode_s"))
            for present, field in ((event["answer_chars"], "first_content_s"),
                                   (event["tool_calls"], "first_tool_call_s")):
                if present and event[field] is None:
                    event[field] = round(time.perf_counter() - started, 6)
            return result
        except Exception as error:
            event.update(outcome="cancelled" if type(error).__name__ == "RequestCancelled" else "error",
                         error_type=type(error).__name__)
            raise
        finally:
            event["duration_s"] = round(time.perf_counter() - started, 6)
            observations(self).record(event)
            print(json.dumps(event, separators=(",", ":")), flush=True)
    return observed


def render_observations(app):
    state = observations(app)
    with state.lock:
        outcomes, finishes = dict(state.outcomes), dict(state.finishes)
        prompt, cached, reasoning, empty = state.prompt, state.cached, state.reasoning, state.empty
        buckets, total = list(state.first_content), state.first_content_sum
    lines = []

    def counter(name, help_text, samples):
        lines.extend([f"# HELP tensorfold:{name} {help_text}", f"# TYPE tensorfold:{name} counter"])
        lines.extend(f"tensorfold:{name}{labels} {value}" for labels, value in samples)

    counter("request_outcomes_total", "Engine requests by completion outcome.",
            [(f'{{outcome="{name}"}}', outcomes.get(name, 0)) for name in ("completed", "truncated", "cancelled", "error")])
    counter("request_success_total", "Engine responses returned, including output-length cutoffs.",
            [(f'{{finish_reason="{name}"}}', finishes.get(name, 0)) for name in ("stop", "length", "tool_calls")])
    counter("prefix_cache_queries_total", "Prompt tokens in returned engine responses.", [("", prompt)])
    counter("prefix_cache_hits_total", "Cached prompt tokens in returned engine responses.", [("", cached)])
    counter("reasoning_tokens_total", "Reasoning tokens in returned engine responses.", [("", reasoning)])
    counter("empty_responses_total", "Returned responses with neither answer text nor tool calls.", [("", empty)])
    name = "tensorfold:first_content_seconds"
    lines.extend([f"# HELP {name} Seconds from engine admission to the first answer delta, excluding reasoning.",
                  f"# TYPE {name} histogram"])
    cumulative = 0
    for edge, count in zip(BUCKETS, buckets):
        cumulative += count
        lines.append(f'{name}_bucket{{le="{edge}"}} {cumulative}')
    lines.extend([f'{name}_bucket{{le="+Inf"}} {cumulative + buckets[-1]}',
                  f"{name}_count {sum(buckets)}", f"{name}_sum {total:.6f}"])
    return "\n".join(lines) + "\n"
