import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "stacks/dgx-spark/scripts/serve-flash.py"
spec = importlib.util.spec_from_file_location("flash_runtime", SCRIPT)
flash = importlib.util.module_from_spec(spec)
spec.loader.exec_module(flash)


class FlashRuntimeTests(unittest.TestCase):
    def test_unsafe_context_concurrency_and_reserve_are_rejected(self) -> None:
        for context, sequences, reserve in ((262145, 4, 8), (512, 1, 8),
                                             (262144, 5, 8), (262144, 0, 8),
                                             (262144, 4, 2), (262144, 4, 33)):
            with self.subTest(context=context, sequences=sequences, reserve=reserve):
                with self.assertRaises(ValueError):
                    flash.serve_command(Path("/snapshot"), context, sequences, reserve)

    def test_tensorfold_uses_exact_snapshot_instead_of_resolving_mutable_hub_ref(self) -> None:
        snapshot = Path("/cache/hub/models--example--flash/snapshots") / ("a" * 40)
        command = flash.serve_command(snapshot, 131072, 2, 10)
        self.assertEqual(command[:3], ["tensorfold", "serve", str(snapshot)])
        self.assertEqual(command[command.index("--context") + 1], "131072")
        self.assertEqual(command[command.index("--parallel") + 1], "2")
        self.assertEqual(command[command.index("--name") + 1], "qwen3.8-flash-next")

    def test_default_requests_do_not_spend_their_budget_only_on_reasoning(self) -> None:
        command = flash.serve_command(Path("/snapshot"), 262144, 4, 8)
        self.assertIn("--no-thinking", command)
        self.assertNotIn("--thinking", command)
        self.assertEqual(command[command.index("--thinking-budget") + 1], "512")
        for budget in (0, -1, 8193):
            with self.assertRaises(ValueError):
                flash.serve_command(Path("/snapshot"), 262144, 4, 8, budget)

    def test_partial_snapshot_is_rejected_until_every_shard_is_present(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            cache = Path(directory)
            revision = "a" * 40
            snapshot = cache / "hub/models--example--flash/snapshots" / revision
            snapshot.mkdir(parents=True)
            (snapshot / "model.safetensors.index.json").write_text(json.dumps({
                "weight_map": {"one": "model-1.safetensors", "two": "model-2.safetensors"},
            }))
            (snapshot / "model-1.safetensors").write_bytes(b"weights")
            with self.assertRaisesRegex(ValueError, "incomplete"):
                flash.snapshot_path(cache, "example/flash", revision)
            (snapshot / "model-2.safetensors").write_bytes(b"weights")
            self.assertEqual(flash.snapshot_path(cache, "example/flash", revision), snapshot)

    def test_model_and_revision_cannot_escape_the_cache_directory(self) -> None:
        for model, revision in (("../flash", "a" * 40), ("example/flash", "../../main")):
            with self.subTest(model=model, revision=revision), self.assertRaises(ValueError):
                flash.snapshot_path(Path("/cache"), model, revision)

    def test_unknown_draft_vocabulary_mode_is_rejected_before_loading(self) -> None:
        with self.assertRaisesRegex(ValueError, "multilingual or english_code"):
            flash.draft_vocabulary(Path("/snapshot"), Path("/cache"), "unexpected")
