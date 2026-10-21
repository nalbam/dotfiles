"""Extend the pinned TensorFold draft shortlist with Hangul and partial UTF-8 tokens."""

import hashlib
import json
import re
import tempfile
from pathlib import Path


def byte_decoder() -> dict[str, int]:
    values = list(range(33, 127)) + list(range(161, 173)) + list(range(174, 256))
    characters = list(values)
    extra = 0
    for value in range(256):
        if value not in values:
            values.append(value)
            characters.append(256 + extra)
            extra += 1
    return {chr(character): value for value, character in zip(values, characters)}


def extend_vocabulary(tokenizer: dict, base: set[int]) -> set[int]:
    if tokenizer.get("decoder", {}).get("type") != "ByteLevel":
        raise ValueError("Multilingual Flash vocabulary requires a ByteLevel tokenizer")
    if not base:
        raise ValueError("The original draft vocabulary must not be empty")
    decoder = byte_decoder()
    selected = set(base)
    for piece, token in tokenizer["model"]["vocab"].items():
        # Literal added/special tokens are retained through the original shortlist.
        if any(character not in decoder for character in piece):
            continue
        raw = bytes(decoder[character] for character in piece)
        try:
            text = raw.decode("utf-8", errors="strict")
        except UnicodeDecodeError:
            # Keeping single bytes does not retain merged, incomplete UTF-8 pieces.
            selected.add(token)
        else:
            if re.search("[가-힣ᄀ-ᇿㄱ-ㅣ]", text):
                selected.add(token)
    return selected


def build_vocabulary(tokenizer_path: Path, base_path: Path, destination: Path) -> dict:
    tokenizer_bytes = tokenizer_path.read_bytes()
    base_bytes = base_path.read_bytes()
    base = {int(value) for value in base_bytes.split()}
    selected = extend_vocabulary(json.loads(tokenizer_bytes), base)
    content = "".join(f"{token}\n" for token in sorted(selected))
    metadata = {"builder": "ko_utf8_v1", "base_ids": len(base), "selected_ids": len(selected),
                "base_sha256": hashlib.sha256(base_bytes).hexdigest(),
                "tokenizer_sha256": hashlib.sha256(tokenizer_bytes).hexdigest(),
                "vocabulary_sha256": hashlib.sha256(content.encode()).hexdigest()}
    destination.parent.mkdir(parents=True, exist_ok=True)
    for path, value in ((destination, content),
                        (destination.with_suffix(".json"), json.dumps(metadata, indent=2) + "\n")):
        if path.is_file() and path.read_text() == value:
            continue
        with tempfile.NamedTemporaryFile("w", dir=path.parent, delete=False) as stream:
            stream.write(value)
            temporary = Path(stream.name)
        temporary.chmod(0o644)
        temporary.replace(path)
    return metadata
