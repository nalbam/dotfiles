#!/usr/bin/env python3
"""Offline regression tests for AI settings deployment and skill generation."""

import json
import os
import runpy
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
import tomllib
import unittest

ROOT = Path(__file__).resolve().parent.parent


class DeploymentTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="dotfiles-ai-")
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name) / "machine home"
        self.repo = self.home / ".dotfiles"
        self.repo.mkdir(parents=True)
        shutil.copy(ROOT / "run.sh", self.repo / "run.sh")
        shutil.copytree(ROOT / "scripts", self.repo / "scripts", ignore=shutil.ignore_patterns("__pycache__"))
        self.put(".dotfiles/claude/CLAUDE.md", "shared instructions\n")
        self.put(".dotfiles/codex/AGENTS.md", "shared Codex instructions\n")
        self.put(".dotfiles/codex/config.toml", 'approval_policy = "on-request"\n[features]\nhooks = true\n')
        self.put(".dotfiles/codex/hooks.json", '{"hooks": {}}\n')
        self.put(".dotfiles/codex/skills/demo/SKILL.md", "demo skill\n")
        self.put(".dotfiles/kiro/agents/default.json", '{}\n')
        self.env = dict(os.environ, HOME=str(self.home), TERM="dumb", PYENV_VERSION="")
        self.bin = Path(self.temp.name) / "bin"
        self.bin.mkdir()
        (self.bin / "python3").symlink_to(sys.executable)
        self.env["PATH"] = str(self.bin) + os.pathsep + os.environ["PATH"]

    def put(self, path, contents):
        target = self.home / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(contents)
        return target

    def sync(self, ok=True):
        result = subprocess.run(["/bin/bash", str(self.repo / "run.sh"), "--vibe"],
                                env=self.env, cwd=self.temp.name, capture_output=True, text=True, timeout=15)
        if ok:
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        else:
            self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        return result

    def test_first_sync_and_repeat(self):
        self.sync()
        target = self.home / ".codex/AGENTS.md"
        self.assertEqual(target.read_text(), "shared Codex instructions\n")
        self.assertTrue((self.home / ".agents/skills/demo/SKILL.md").is_file())
        stamp = target.stat().st_mtime_ns
        self.sync()
        self.assertEqual(target.stat().st_mtime_ns, stamp)

    def test_preserve_unmanaged_legacy_names(self):
        paths = [".codex/skills/custom/SKILL.md", ".claude/skills/security-review/SKILL.md"]
        for path in paths:
            self.put(path, "user installed\n")
        self.sync()
        for path in paths:
            self.assertEqual((self.home / path).read_text(), "user installed\n")

    def test_changed_file_is_backed_up(self):
        target = self.put(".codex/AGENTS.md", "local instructions\n")
        self.sync()
        backup = target.with_name(target.name + ".backup")
        self.assertEqual(backup.read_text(), "local instructions\n")
        self.assertEqual(backup.stat().st_mode & 0o777, 0o600)
        self.sync()
        self.assertEqual(backup.read_text(), "local instructions\n")

    def test_prune_managed_only_and_backup(self):
        self.sync()
        self.put(".agents/skills/local/SKILL.md", "personal\n")
        (self.repo / "codex/skills/demo/SKILL.md").unlink()
        self.put(".dotfiles/codex/skills/new/SKILL.md", "new\n")
        self.sync()
        self.assertFalse((self.home / ".agents/skills/demo/SKILL.md").exists())
        self.assertEqual((self.home / ".agents/skills/demo/SKILL.md.backup").read_text(), "demo skill\n")
        self.assertTrue((self.home / ".agents/skills/local/SKILL.md").is_file())

    def test_missing_source_preserves_manifest(self):
        self.sync()
        manifest = self.home / ".toast/vibe_manifest_codex_skills"
        old = manifest.read_bytes()
        shutil.rmtree(self.repo / "codex/skills")
        self.sync()
        self.assertEqual(manifest.read_bytes(), old)
        self.assertTrue((self.home / ".agents/skills/demo/SKILL.md").exists())

    def test_toml_comments_indentation_nested_tables(self):
        self.put(".dotfiles/codex/config.toml", 'approval_policy = "on-request"\n[features]\nhooks = true\nnew_flag = true\n[permissions.work]\nnetwork = true\n')
        target = self.put(".codex/config.toml", ' approval_policy = "never" # user choice\n [features] # existing\n hooks = false\n [projects."/a/b"]\n trust_level = "trusted"\n')
        self.sync()
        config = tomllib.loads(target.read_text())
        self.assertEqual(config["approval_policy"], "never")
        self.assertEqual(config["features"], {"hooks": False, "new_flag": True})
        self.assertEqual(config["permissions"]["work"]["network"], True)
        self.assertEqual(config["projects"]["/a/b"]["trust_level"], "trusted")
        self.assertIn("# user choice", target.read_text())
        self.sync()

    def test_json_preserves_existing_values(self):
        self.put(".dotfiles/claude/settings.json", '{"env":{"NEW":"yes"},"hooks":{"SessionStart":[1]},"flag":true}\n')
        target = self.put(".claude/settings.json", '{"env":{"CUSTOM":"local"},"hooks":{"SessionStart":[]},"flag":false}\n')
        self.sync()
        self.assertEqual(json.loads(target.read_text()), {"env":{"NEW":"yes","CUSTOM":"local"},"hooks":{"SessionStart":[]},"flag":False})

    def test_invalid_json_does_not_commit_manifest(self):
        self.sync()
        self.put(".dotfiles/claude/settings.json", '{"hooks": {}}')
        target = self.put(".claude/settings.json", '{broken')
        manifest = self.home / ".toast/vibe_manifest_claude"
        old = manifest.read_bytes()
        result = self.sync(ok=False)
        self.assertEqual(target.read_text(), '{broken')
        self.assertEqual(manifest.read_bytes(), old)
        self.assertNotIn("AI tools sync complete", result.stdout)

    def test_invalid_new_config_is_rejected(self):
        self.put(".dotfiles/codex/config.toml", 'bad = [')
        self.sync(ok=False)
        self.assertFalse((self.home / ".codex/config.toml").exists())

    def test_malformed_rule_markers_preserve_local_rules(self):
        self.put(".dotfiles/codex/rules/default.rules", '# BEGIN dotfiles managed codex rules\nnew rule\n# END dotfiles managed codex rules\n')
        target = self.put(".codex/rules/default.rules", '# END dotfiles managed codex rules\nlocal rule\n# BEGIN dotfiles managed codex rules\n')
        old = target.read_text()
        self.sync(ok=False)
        self.assertEqual(target.read_text(), old)

    def test_rules_preserve_local_content(self):
        self.put(".dotfiles/codex/rules/default.rules", '# BEGIN dotfiles managed codex rules\nnew rule\n# END dotfiles managed codex rules\n')
        target = self.put(".codex/rules/default.rules", 'before\n# BEGIN dotfiles managed codex rules\nold rule\n# END dotfiles managed codex rules\nafter\n')
        self.sync()
        self.assertEqual(target.read_text(), 'before\n# BEGIN dotfiles managed codex rules\nnew rule\n# END dotfiles managed codex rules\nafter\n')

    def test_no_configuration_values_in_output(self):
        self.put(".dotfiles/claude/settings.json", '{"env":{"NEW":"yes"}}')
        self.put(".claude/settings.json", '{"env":{"TOKEN":"private-test-value"}}')
        result = self.sync()
        self.assertNotIn("private-test-value", result.stdout + result.stderr)

    def test_symlink_destination_is_preserved(self):
        target = self.put("external.txt", "do not change\n")
        (self.home / ".codex").mkdir()
        (self.home / ".codex/AGENTS.md").symlink_to(target)
        self.sync(ok=False)
        self.assertEqual(target.read_text(), "do not change\n")


    def test_real_repository_payload(self):
        for name, _ in (("claude", ".claude"), ("codex", ".codex"), ("kiro", ".kiro")):
            shutil.rmtree(self.repo / name)
            shutil.copytree(ROOT / name, self.repo / name)
        self.sync()
        self.sync()
        for source_name, destination in (("claude", ".claude"), ("codex", ".codex"), ("codex/skills", ".agents/skills")):
            for source in (self.repo / source_name).rglob("*.md"):
                relative = source.relative_to(self.repo / source_name)
                if source_name == "codex" and relative.parts[0] == "skills":
                    continue
                self.assertEqual(source.read_bytes(), (self.home / destination / relative).read_bytes())
        self.assertEqual(tomllib.loads((self.repo / "codex/config.toml").read_text()),
                         tomllib.loads((self.home / ".codex/config.toml").read_text()))

    def test_corrupt_manifest_cannot_escape_target(self):
        self.sync()
        protected = self.put("keep.md", "personal data")
        self.put(".toast/vibe_manifest_codex", "../keep.md\n")
        self.sync(ok=False)
        self.assertEqual(protected.read_text(), "personal data")

    def test_locked_sync_fails_before_deployment(self):
        import fcntl
        lock = self.put(".toast/ai-sync.lock", "")
        with lock.open("a") as stream:
            fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
            self.sync(ok=False)
        self.assertFalse((self.home / ".codex/AGENTS.md").exists())
        self.sync()


    def test_failed_atomic_write_preserves_file_and_manifest(self):
        from unittest.mock import patch
        module = runpy.run_path(str(ROOT / "scripts/sync-ai-tools.py"))
        self.sync()
        target = self.home / ".codex/AGENTS.md"
        manifest = self.home / ".toast/vibe_manifest_codex"
        old_manifest = manifest.read_bytes()
        self.put(".dotfiles/codex/AGENTS.md", "changed instructions")
        self.put(".dotfiles/codex/new.md", "new instructions")
        real_replace = os.replace
        def fail_replace(source, destination):
            if Path(destination) == target:
                raise OSError("simulated disk failure")
            return real_replace(source, destination)
        with patch("pathlib.Path.home", return_value=self.home), patch("os.replace", side_effect=fail_replace):
            self.assertEqual(module["main"](), 1)
        self.assertEqual(target.read_text(), "shared Codex instructions\n")
        self.assertEqual(manifest.read_bytes(), old_manifest)
        self.assertFalse((self.home / ".codex/new.md").exists())
        self.sync()
        self.assertEqual(target.read_text(), "changed instructions")

    def test_executable_hook_mode_is_deployed(self):
        source = self.put(".dotfiles/claude/hooks/tool.sh", "#!/bin/bash\nexit 0\n")
        source.chmod(0o755)
        target = self.put(".claude/hooks/tool.sh", source.read_text())
        target.chmod(0o600)
        self.sync()
        self.assertTrue(target.stat().st_mode & 0o100)

    def test_inline_toml_conflict_is_reported_without_writes(self):
        self.put(".dotfiles/codex/config.toml", "[features]\nhooks = true\nnew_flag = true\n")
        target = self.put(".codex/config.toml", "features = { hooks = false }\n")
        self.sync(ok=False)
        self.assertEqual(target.read_text(), "features = { hooks = false }\n")
        self.assertFalse((self.home / ".claude/CLAUDE.md").exists())


    def test_claude_update_timestamp_only_after_success(self):
        source = (ROOT / "run.sh").read_text()
        start = source.index("# Claude Code 업데이트")
        block = source[start:source.index("# PIP 패키지 설치 (버전 체크 포함)", start)]
        (self.home / ".toast").mkdir(exist_ok=True)
        marker = self.home / ".toast/last_update_claude"
        for status in (1, 0):
            prelude = "_should_update() { return 0; }; _run() { :; }; _ok() { :; }; _skip() { :; }; _warn() { :; };\n"
            prelude += "claude() { return " + str(status) + "; };\n"
            result = subprocess.run(["/bin/bash", "-c", prelude + block], env=self.env,
                                    capture_output=True, text=True, timeout=5)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(marker.exists(), status == 0)


class GeneratorTests(unittest.TestCase):
    def setUp(self):
        self.module = runpy.run_path(str(ROOT / "scripts/gen-codex-skills.py"))

    def test_multiline_frontmatter_is_removed(self):
        source = "---\nname: example\nallowed-tools:\n  - Read\n  - Bash\ndescription: example\n---\nbody\n"
        expected = "---\nname: example\ndescription: example\n---\nbody\n"
        self.assertEqual(self.module["strip_claude_frontmatter"](source), expected)

    def test_tool_specific_sections_and_project_names(self):
        transform = self.module["transform"]
        source = (ROOT / "claude/skills/claude-code-usage/SKILL.md").read_text()
        result = transform("claude-code-usage", source)
        self.assertNotIn("EnterPlanMode", result)
        self.assertIn("## Codex", result)
        self.assertIn("## Subagents", result)
        self.assertEqual(transform("docs-read", "CLAUDE.md / AGENTS.md"), "CLAUDE.md / AGENTS.md")

    def test_stale_references_and_deleted_skills(self):
        with tempfile.TemporaryDirectory(prefix="dotfiles-generator-") as tmp:
            fixture = Path(tmp)
            shutil.copytree(ROOT / "scripts", fixture / "scripts", ignore=shutil.ignore_patterns("__pycache__"))
            shutil.copytree(ROOT / "claude/skills", fixture / "claude/skills")
            shutil.copytree(ROOT / "codex/skills", fixture / "codex/skills")
            command = [sys.executable, str(fixture / "scripts/gen-codex-skills.py")]
            metadata = {p: p.read_bytes() for p in (fixture / "codex/skills").rglob("*.yaml")}
            stale = fixture / "codex/skills/nextjs-init/references/setup.md"
            (fixture / "claude/skills/nextjs-init/references/setup.md").unlink()
            shutil.rmtree(fixture / "claude/skills/commit")
            result = subprocess.run(command + ["--check"], capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertTrue(stale.exists())
            result = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertFalse(stale.exists())
            self.assertFalse((fixture / "codex/skills/commit/SKILL.md").exists())
            self.assertTrue(all(p.read_bytes() == data for p, data in metadata.items()))
            self.assertEqual(subprocess.run(command + ["--check"], capture_output=True).returncode, 0)


class MemoryHookTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="dotfiles-memory-")
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name)
        self.repo = self.home / ".claude-memory"
        (self.repo / ".git").mkdir(parents=True)
        self.bin = self.home / "bin"
        self.bin.mkdir()
        self.env = dict(os.environ, HOME=str(self.home), PATH=str(self.bin) + os.pathsep + os.environ["PATH"])
        self.log = self.home / "git-calls"
        self.hook = ROOT / "claude/hooks/memory-sync.sh"

    def fake_git(self, body):
        script = self.bin / "git"
        script.write_text('#!/bin/bash\nprintf "%s\\n" "$*" >> "$HOME/git-calls"\n' + body)
        script.chmod(0o700)

    def invoke(self, *args):
        return subprocess.run(["/bin/bash", str(self.hook), *args], env=self.env,
                              capture_output=True, text=True, timeout=5)

    def test_failed_pull_does_not_push(self):
        self.fake_git('case "$*" in *"pull --rebase"*) exit 1;; esac\nexit 0\n')
        self.assertNotEqual(self.invoke("sync").returncode, 0)
        self.assertNotIn("push", self.log.read_text())
        self.assertFalse((self.repo / ".sync.lock").exists())
        self.assertIn("exclude", self.log.read_text())

    def test_failed_stage_does_not_commit_or_pull(self):
        self.fake_git('case "$*" in *" add "*) exit 1;; esac\nexit 0\n')
        self.assertNotEqual(self.invoke("sync").returncode, 0)
        self.assertNotIn("commit", self.log.read_text())
        self.assertNotIn("pull", self.log.read_text())

    def test_failed_diff_does_not_commit(self):
        self.fake_git('case "$*" in *" diff "*) exit 128;; esac\nexit 0\n')
        self.assertNotEqual(self.invoke("sync").returncode, 0)
        self.assertNotIn("commit", self.log.read_text())
        self.assertNotIn("pull", self.log.read_text())

    def test_unfinished_rebase_is_not_committed(self):
        self.fake_git("exit 0\n")
        (self.repo / ".git/rebase-merge").mkdir()
        self.assertNotEqual(self.invoke("sync").returncode, 0)
        self.assertFalse(self.log.exists())
        self.assertFalse((self.repo / ".sync.lock").exists())

    def test_existing_migration_backup_is_preserved(self):
        self.fake_git("exit 0\n")
        project = self.home / "workspace/project"
        project.mkdir(parents=True)
        import re
        slug = re.sub(r"[^a-zA-Z0-9]", "-", str(project))
        memory = self.home / ".claude/projects" / slug / "memory"
        memory.mkdir(parents=True)
        (memory / "MEMORY.md").write_text("current memory")
        old = memory.with_name("memory.backup")
        old.mkdir()
        (old / "MEMORY.md").write_text("previous backup")
        self.assertNotEqual(self.invoke("link", str(project)).returncode, 0)
        self.assertFalse(memory.is_symlink())
        self.assertEqual((old / "MEMORY.md").read_text(), "previous backup")
        self.assertEqual((memory / "MEMORY.md").read_text(), "current memory")

    def test_start_does_not_wait_for_first_clone(self):
        shutil.rmtree(self.repo)
        self.fake_git('case "$*" in "clone "*) sleep 1; exit 1;; esac\nexit 0\n')
        started = time.monotonic()
        self.assertEqual(self.invoke("start").returncode, 0)
        self.assertLess(time.monotonic() - started, 0.8)
        time.sleep(1.1)


if __name__ == "__main__":
    unittest.main()
