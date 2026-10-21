import contextlib
import importlib.util
import io
import json
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1] / "stacks/dgx-spark/tensorfold"


def load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


prefixes, observation, policy = load("prefixes"), load("observability"), load("policy")


class ThinkingBudgetTests(unittest.TestCase):
    def test_default_budget_reserves_answer_space_for_small_requests(self):
        self.assertEqual(policy.thinking_budget(None, 512, 128, True), 64)
        self.assertEqual(policy.thinking_budget(0, 512, 2048, True), 512)

    def test_explicit_budget_is_preserved_and_disabled_thinking_spends_none(self):
        self.assertEqual(policy.thinking_budget(96, 512, 128, True), 96)
        self.assertEqual(policy.thinking_budget(96, 512, 128, False), 0)


class State:
    def __init__(self, name):
        self.name, self.copied = name, None

    def copy_prefix(self, source, length, mtp_length):
        self.copied = (source, length, mtp_length)


class Owner:
    def __init__(self):
        self.source, self.idle = State("source"), State("idle")
        self.kept = [([1, 2, 3], self.source, {"mtp_len": 3}, None),
                     ([9], self.idle, {"mtp_len": 1}, None)]
        self.free, self.depth, self.keep = [], 6, 8
        self.busy = {id(self.source)}
        self.fits, self.protected = True, None
        self.shrunk = []

    def _busy(self):
        return self.busy

    def _drop_kept(self, state):
        self.kept = [entry for entry in self.kept if entry[1] is not state]

    def _grow(self, state, length, protect):
        self.protected = protect
        return self.fits

    def _shrink(self, state, force=False):
        self.shrunk.append(state)


class PrefixTests(unittest.TestCase):
    def test_recycles_idle_retained_slot_and_copies_busy_shared_prefix(self):
        owner = Owner()
        state, resume, cached = prefixes.slot_for(owner, [1, 2, 3, 4], True)
        self.assertIs(state, owner.idle)
        self.assertEqual(cached, 3)
        self.assertEqual(state.copied, (owner.source, 3, 3))
        self.assertIs(owner.protected, owner.source)
        self.assertEqual(resume["state"], {"mtp_len": 3})
        self.assertEqual([entry[1] for entry in owner.kept], [owner.source])

    def test_never_recycles_a_busy_slot_or_the_copy_source(self):
        owner = Owner()
        owner.busy.add(id(owner.idle))
        with self.assertRaisesRegex(RuntimeError, "no free stream slot"):
            prefixes.slot_for(owner, [1, 2, 3, 4], True)
        self.assertEqual(len(owner.kept), 2)
        self.assertIsNone(owner.idle.copied)

    def test_copy_still_obeys_memory_admission(self):
        owner = Owner()
        owner.fits = False
        state, resume, cached = prefixes.slot_for(owner, [1, 2, 3, 4], True)
        self.assertIs(state, owner.idle)
        self.assertIsNone(resume)
        self.assertEqual(cached, 0)
        self.assertIsNone(owner.idle.copied)
        self.assertIs(owner.kept[0][1], owner.source)

    def test_copy_error_returns_spare_and_preserves_original_error(self):
        owner = Owner()
        error = RuntimeError("copy failed")
        with patch.object(owner.idle, "copy_prefix", side_effect=error):
            with self.assertRaises(RuntimeError) as caught:
                prefixes.slot_for(owner, [1, 2, 3, 4], True)
        self.assertIs(caught.exception, error)
        self.assertEqual(owner.free, [owner.idle])
        self.assertEqual(owner.shrunk, [owner.idle])
        self.assertIs(owner.kept[0][1], owner.source)

    def test_idle_matching_slot_reuses_cache_without_copy(self):
        owner = Owner()
        owner.busy.clear()
        state, _, cached = prefixes.slot_for(owner, [1, 2, 3, 4], True)
        self.assertIs(state, owner.source)
        self.assertEqual(cached, 3)
        self.assertIsNone(state.copied)

    def test_fork_preserves_the_longer_prefix_on_an_idle_source(self):
        owner = Owner()
        owner.busy.clear()
        owner.kept.append(([1, 2, 3, 99], owner.source, {"mtp_len": 4}, None))
        state, _, cached = prefixes.slot_for(owner, [1, 2, 3, 4], True)
        self.assertIs(state, owner.idle)
        self.assertEqual(cached, 3)
        self.assertEqual([entry[0] for entry in owner.kept], [[1, 2, 3], [1, 2, 3, 99]])


class ObservabilityTests(unittest.TestCase):
    def test_records_metadata_without_prompt_answer_reasoning_or_credentials(self):
        app = SimpleNamespace()
        clock = [10.0]
        result = dict(finish="stop", prompt_tokens=50, cached_tokens=40, completion_tokens=12,
                      reasoning_tokens=5, content="PRIVATE ANSWER", calls=[], stats={"prefill_s": 0.2, "decode_s": 0.8})

        @observation.observe_request
        def run(self, body, chat, emit, **kwargs):
            clock[0] = 10.2
            emit({"reasoning_content": "PRIVATE REASONING"})
            clock[0] = 10.8
            emit({"content": "PRIVATE ANSWER"})
            clock[0] = 11.0
            return result

        output = io.StringIO()
        prepared = SimpleNamespace(thinking=True, think_budget=16, max_tokens=64, prompt=list(range(50)))
        with contextlib.redirect_stdout(output), patch.object(observation.time, "perf_counter", side_effect=lambda: clock[0]):
            actual = run(app, {"messages": ["PRIVATE PROMPT"], "api_key": "PRIVATE KEY", "stream": True},
                         True, lambda delta: True, prepared=prepared)
        self.assertIs(actual, result)
        self.assertNotIn("PRIVATE", output.getvalue())
        events = [json.loads(line) for line in output.getvalue().splitlines()]
        self.assertEqual(events[0]["event"], "flash_request_started")
        self.assertEqual(events[0]["request_id"], events[1]["request_id"])
        event = events[1]
        self.assertEqual(event["first_content_s"], 0.8)
        self.assertEqual(event["first_reasoning_s"], 0.2)
        self.assertEqual(event["duration_s"], 1.0)
        metrics = observation.render_observations(app)
        self.assertIn("tensorfold:prefix_cache_hits_total 40", metrics)
        self.assertIn("tensorfold:prefix_cache_queries_total 50", metrics)
        self.assertIn('tensorfold:request_success_total{finish_reason="stop"} 1', metrics)

    def test_cancelled_request_is_not_reported_as_success_and_error_is_rethrown(self):
        class RequestCancelled(Exception):
            pass
        error = RequestCancelled("PRIVATE detail")
        app = SimpleNamespace()

        @observation.observe_request
        def run(*args, **kwargs):
            raise error

        output = io.StringIO()
        with contextlib.redirect_stdout(output), self.assertRaises(RequestCancelled) as caught:
            run(app, {}, True, lambda delta: True)
        self.assertIs(caught.exception, error)
        self.assertNotIn("PRIVATE", output.getvalue())
        self.assertEqual(json.loads(output.getvalue().splitlines()[-1])["outcome"], "cancelled")
        metrics = observation.render_observations(app)
        self.assertIn('tensorfold:request_outcomes_total{outcome="cancelled"} 1', metrics)
        self.assertIn('tensorfold:request_success_total{finish_reason="stop"} 0', metrics)

    def test_empty_truncation_is_counted_separately(self):
        app = SimpleNamespace()

        @observation.observe_request
        def run(*args, **kwargs):
            return dict(finish="length", prompt_tokens=20, cached_tokens=0, completion_tokens=8,
                        reasoning_tokens=8, content="", calls=None, stats={})

        with contextlib.redirect_stdout(io.StringIO()):
            run(app, {}, True, lambda delta: True)
        metrics = observation.render_observations(app)
        self.assertIn('tensorfold:request_outcomes_total{outcome="truncated"} 1', metrics)
        self.assertIn("tensorfold:empty_responses_total 1", metrics)
        self.assertIn("tensorfold:first_content_seconds_count 0", metrics)
