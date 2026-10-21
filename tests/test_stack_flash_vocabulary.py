import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "stacks/dgx-spark/scripts/flash-vocabulary.py"
spec = importlib.util.spec_from_file_location("flash_vocabulary", SCRIPT)
vocabulary = importlib.util.module_from_spec(spec)
spec.loader.exec_module(vocabulary)


class FlashVocabularyTests(unittest.TestCase):
    def tokenizer(self) -> dict:
        encoder = {value: character for character, value in vocabulary.byte_decoder().items()}
        def piece(data: bytes) -> str:
            return "".join(encoder[value] for value in data)
        return {"decoder": {"type": "ByteLevel"}, "model": {"vocab": {
            " retained": 1, " unseen": 2,
            piece("합니다".encode()): 3,
            piece(bytes([0xED, 0x95])): 4,
            piece(bytes([0x80, 0x81])): 5,
        }}}

    def test_keeps_original_ids_and_adds_hangul_and_incomplete_utf8_merges(self) -> None:
        selected = vocabulary.extend_vocabulary(self.tokenizer(), {1, 99})
        self.assertEqual(selected, {1, 3, 4, 5, 99})
        self.assertNotIn(2, selected)

    def test_rejects_unsupported_tokenizer_instead_of_building_wrong_ids(self) -> None:
        tokenizer = self.tokenizer()
        tokenizer["decoder"]["type"] = "WordPiece"
        with self.assertRaisesRegex(ValueError, "ByteLevel"):
            vocabulary.extend_vocabulary(tokenizer, {1})

    def test_rejects_empty_original_vocabulary(self) -> None:
        with self.assertRaisesRegex(ValueError, "must not be empty"):
            vocabulary.extend_vocabulary(self.tokenizer(), set())

    def test_output_is_reproducible_and_records_input_hashes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            tokenizer = root / "tokenizer.json"
            base = root / "base.txt"
            output = root / "generated.txt"
            tokenizer.write_text(json.dumps(self.tokenizer()))
            base.write_text("99\n1\n1\n")
            first = vocabulary.build_vocabulary(tokenizer, base, output)
            before = output.stat().st_mtime_ns
            second = vocabulary.build_vocabulary(tokenizer, base, output)
            self.assertEqual(output.read_text(), "1\n3\n4\n5\n99\n")
            self.assertEqual(first, second)
            self.assertEqual(output.stat().st_mtime_ns, before)
            self.assertEqual(first["base_ids"], 2)
            self.assertEqual(json.loads(output.with_suffix(".json").read_text()), first)
