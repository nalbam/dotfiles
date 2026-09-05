#!/usr/bin/env python3
"""Deploy AI settings from ~/.dotfiles using only Python 3.11+ standard libraries."""

import sys

if sys.version_info < (3, 11):
    sys.exit("AI sync requires Python 3.11 or newer; no files were changed.")

from contextlib import contextmanager
from datetime import date, datetime, time
import fcntl
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import stat
import tempfile
import tomllib

TARGETS = (("claude", ".claude"), ("codex", ".codex"),
           ("codex/skills", ".agents/skills"), ("kiro", ".kiro"))
JSON_SETTINGS = {("claude", "settings.json"), ("codex", "hooks.json"),
                 ("kiro", "agents/default.json")}
BEGIN = "# BEGIN dotfiles managed codex rules"
END = "# END dotfiles managed codex rules"


def regular_path(path, boundary):
    """Refuse symlinks and non-regular destinations before reading or replacing them."""
    current = path
    while current != boundary:
        if current.is_symlink():
            raise ValueError(f"Symlink requires manual review: {current}")
        current = current.parent
    if path.exists() and not path.is_file():
        raise ValueError(f"Expected a regular file: {path}")


def fill_missing(local, defaults):
    if not isinstance(local, dict) or not isinstance(defaults, dict):
        return local
    return {key: fill_missing(value, defaults[key]) if key in defaults else value
            for key, value in local.items()} | {key: value for key, value in defaults.items() if key not in local}


def toml_value(value):
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, str):
        return json.dumps(value, ensure_ascii=False)
    if isinstance(value, (datetime, date, time)):
        return value.isoformat()
    if isinstance(value, (int, float)):
        return repr(value)
    if isinstance(value, list):
        return "[" + ", ".join(toml_value(item) for item in value) + "]"
    if isinstance(value, dict):
        return "{ " + ", ".join(f"{json.dumps(key)} = {toml_value(item)}" for key, item in value.items()) + " }"
    raise ValueError("Unsupported TOML default value")


def missing_leaves(local, defaults, prefix=()):
    for key, value in defaults.items():
        path = prefix + (key,)
        if key not in local:
            if isinstance(value, dict) and value:
                yield from missing_leaves({}, value, path)
            else:
                yield path, value
        elif isinstance(local[key], dict) and isinstance(value, dict):
            yield from missing_leaves(local[key], value, path)


def table_path(line):
    if not line.lstrip().startswith("[") or line.lstrip().startswith("[["):
        return None
    try:
        table = tomllib.loads(line + '\n__dotfiles_probe__ = true\n')
    except tomllib.TOMLDecodeError:
        return None
    path = ()
    while isinstance(table, dict) and "__dotfiles_probe__" not in table and len(table) == 1:
        key, table = next(iter(table.items()))
        path += (key,)
    return path if table == {"__dotfiles_probe__": True} else None


def merge_toml(source, old):
    defaults = tomllib.loads(source)
    if old is None:
        return source
    local = tomllib.loads(old)
    expected = fill_missing(local, defaults)
    if expected == local:
        return old
    lines = old.splitlines(keepends=True)
    tables = {(): 0}
    for index, line in enumerate(lines):
        path = table_path(line)
        if path:
            tables[path] = index + 1
    insertions = {}
    for path, value in missing_leaves(local, defaults):
        parent = max((table for table in tables if len(table) < len(path) and path[:len(table)] == table), key=len)
        key = ".".join(json.dumps(part, ensure_ascii=False) for part in path[len(parent):])
        insertions.setdefault(tables[parent], []).append(f"{key} = {toml_value(value)}\n")
    for index in sorted(insertions, reverse=True):
        if index and not lines[index - 1].endswith("\n"):
            lines[index - 1] += "\n"
        lines[index:index] = insertions[index]
    result = "".join(lines)
    if tomllib.loads(result) != expected:
        raise ValueError("TOML merge could not preserve existing settings; review the config manually")
    return result


def rule_block(text):
    lines = text.splitlines(keepends=True)
    starts = [i for i, line in enumerate(lines) if line.rstrip("\r\n") == BEGIN]
    ends = [i for i, line in enumerate(lines) if line.rstrip("\r\n") == END]
    if not starts and not ends:
        return lines, None
    if len(starts) != 1 or len(ends) != 1 or starts[0] >= ends[0]:
        raise ValueError("Invalid Codex managed-rule markers")
    return lines, (starts[0], ends[0] + 1)


def merge_rules(source, old):
    lines, span = rule_block(source)
    if span is None:
        raise ValueError("Missing Codex managed-rule markers")
    managed = "".join(lines[span[0]:span[1]])
    if not managed.endswith("\n"):
        managed += "\n"
    if old is None:
        return source
    lines, span = rule_block(old)
    if span is None:
        return managed + "\n" + old
    return "".join(lines[:span[0]]) + managed + "".join(lines[span[1]:])


def file_content(source, destination, source_name, relative):
    data = source.read_bytes()
    old = destination.read_bytes() if destination.exists() else None
    try:
        if source_name == "codex" and relative == "config.toml":
            return merge_toml(data.decode(), old.decode() if old is not None else None).encode()
        if source_name == "codex" and relative == "rules/default.rules":
            return merge_rules(data.decode(), old.decode() if old is not None else None).encode()
        if (source_name, relative) in JSON_SETTINGS:
            defaults = json.loads(data)
            local = json.loads(old) if old is not None else {}
            if not isinstance(defaults, dict) or not isinstance(local, dict):
                raise ValueError("Settings must be JSON objects")
            merged = fill_missing(local, defaults)
            if old is not None and merged == local:
                return old
            return (json.dumps(merged, ensure_ascii=False, indent=2) + "\n").encode()
    except (ValueError, UnicodeError) as error:
        # Config values can contain credentials; report the location, never their contents.
        raise ValueError(f"Cannot merge {source_name}/{relative} ({type(error).__name__}); files preserved") from None
    return data


def atomic_write(path, data, mode):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            os.fchmod(stream.fileno(), mode)
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def backup(path, boundary):
    target = path.with_name(path.name + ".backup")
    regular_path(target, boundary)
    atomic_write(target, path.read_bytes(), 0o600)


def source_files(directory):
    if directory.is_symlink():
        raise ValueError(f"Source symlink requires manual review: {directory}")
    files = []
    for parent, directories, names in os.walk(directory):
        directories[:] = sorted(name for name in directories if name != "__pycache__")
        for name in directories + names:
            path = Path(parent) / name
            if path.is_symlink():
                raise ValueError(f"Source symlink requires manual review: {path}")
        for name in names:
            if not (Path(parent) / name).is_file():
                raise ValueError(f"Expected a regular source file: {Path(parent) / name}")
        files.extend(Path(parent) / name for name in sorted(names) if not name.endswith((".pyc", ".backup")))
    return sorted(files)


def plan_target(home, repo, source_name, target_name):
    source = repo / source_name
    if not source.is_dir():
        print(f"SKIP: {source_name} (source missing; deployed files preserved)")
        return [], None
    files = [path for path in source_files(source)
             if source_name != "codex" or path.relative_to(source).parts[0] != "skills"]
    if not files:
        print(f"SKIP: {source_name} (source empty; deployed files preserved)")
        return [], None
    destination = home / target_name
    manifest = home / ".toast" / ("vibe_manifest_" + source_name.replace("/", "_"))
    regular_path(manifest, home)
    changes, names = [], set()
    for path in files:
        relative = path.relative_to(source).as_posix()
        if "\n" in relative or "\r" in relative or "\\" in relative:
            raise ValueError(f"Filename cannot be represented in a manifest: {source_name}")
        names.add(relative)
        target = destination / relative
        regular_path(target, home)
        regular_path(target.with_name(target.name + ".backup"), home)
        content = file_content(path, target, source_name, relative)
        executable = path.stat().st_mode & 0o100
        mode = (stat.S_IMODE(target.stat().st_mode) if target.exists() else 0o600) | executable
        if (target.exists() and stat.S_IMODE(target.stat().st_mode) == mode
                and hashlib.md5(target.read_bytes()).digest() == hashlib.md5(content).digest()):
            continue
        changes.append((target, content, mode))
    if manifest.exists():
        for relative in sorted(set(manifest.read_text().splitlines()) - names):
            parts = PurePosixPath(relative).parts
            if not parts or PurePosixPath(relative).is_absolute() or ".." in parts or "\\" in relative:
                raise ValueError(f"Invalid managed path in {manifest}")
            target = destination / relative
            regular_path(target, home)
            regular_path(target.with_name(target.name + ".backup"), home)
            if target.exists():
                changes.append((target, None, None))
    return changes, (manifest, ("\n".join(sorted(names)) + "\n").encode())


@contextmanager
def sync_lock(home):
    path = home / ".toast/ai-sync.lock"
    regular_path(path, home)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a") as stream:
        os.chmod(path, 0o600)
        try:
            fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise ValueError("Another AI sync is running; retry after it finishes") from None
        yield


def main():
    home = Path.home().resolve()
    repo = home / ".dotfiles"
    if not repo.is_dir():
        sys.exit("Dotfiles not installed: ~/.dotfiles")
    try:
        with sync_lock(home):
            plans = [plan_target(home, repo, *target) for target in TARGETS]
            updated = pruned = 0
            for changes, _ in plans:
                for path, content, mode in changes:
                    if path.exists():
                        backup(path, home)
                    if content is None:
                        path.unlink()
                        pruned += 1
                        print(f"PRUNE: ~/{path.relative_to(home)} (backup preserved)")
                    else:
                        atomic_write(path, content, mode)
                        updated += 1
                        print(f"SYNC: ~/{path.relative_to(home)}")
            # Only acknowledge managed files once every target was deployed successfully.
            for _, manifest in plans:
                if manifest:
                    path, data = manifest
                    if not path.exists() or path.read_bytes() != data:
                        atomic_write(path, data, 0o600)
            print(f"Sync summary: {updated} written, {pruned} pruned")
    except (OSError, ValueError) as error:
        print(f"AI sync failed: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
