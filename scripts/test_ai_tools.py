#!/usr/bin/env python3
"""Offline regression tests for AI settings deployment and skill generation."""

import json
import os
import re
import runpy
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
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
        self.put(".dotfiles/opencode/AGENTS.md", "shared OpenCode instructions\n")
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
        self.put(".dotfiles/claude/settings.json", '{"env":{"NEW":"yes"},"list":[1],"flag":true}\n')
        target = self.put(".claude/settings.json", '{"env":{"CUSTOM":"local"},"list":[],"flag":false}\n')
        self.sync()
        self.assertEqual(json.loads(target.read_text()), {"env":{"NEW":"yes","CUSTOM":"local"},"list":[],"flag":False})

    def machine_hook(self, command="bash ~/.claude/hooks/machine.sh start", timeout=5):
        return {"type": "command", "command": command, "timeout": timeout}

    def configure_machine_hooks(self):
        self.put(".dotfiles/claude/hooks/machine.sh", "#!/bin/bash\nexit 0\n")
        desired = {"hooks": [self.machine_hook()]}
        self.put(".dotfiles/claude/settings.json", json.dumps({"hooks": {"SessionStart": [desired]}}))
        return desired

    def test_machine_hooks_join_existing_vibemon_event(self):
        desired = self.configure_machine_hooks()
        foreign = {"matcher": "startup|resume|clear", "hooks": [
            {"type": "command", "command": "python3 ~/.claude/hooks/vibemon.py", "async": True}]}
        target = self.put(".claude/settings.json", json.dumps({"hooks": {"SessionStart": [foreign]}}))
        self.sync()
        self.assertEqual(json.loads(target.read_text())["hooks"]["SessionStart"], [foreign, desired])
        first = target.read_bytes(), target.stat().st_mtime_ns
        self.sync()
        self.assertEqual((target.read_bytes(), target.stat().st_mtime_ns), first)

    def test_machine_hooks_refresh_only_owned_script_across_matchers_and_events(self):
        desired = self.configure_machine_hooks()
        foreign = {"type": "command", "command": "python3 ~/.claude/hooks/vibemon.py"}
        other_path = self.machine_hook("bash /another/machine.sh start")
        mention = self.machine_hook("echo ~/.claude/hooks/machine.sh")
        stale = self.machine_hook('bash "${HOME}/.claude/hooks/machine.sh" old', 99)
        target = self.put(".claude/settings.json", json.dumps({"hooks": {
            "SessionStart": [{"matcher": "startup", "hooks": [foreign, stale, other_path, mention]}],
            "Stop": [{"hooks": [stale]}]}}))
        self.sync()
        self.assertEqual(json.loads(target.read_text())["hooks"], {"SessionStart": [
            {"matcher": "startup", "hooks": [foreign, other_path, mention]}, desired]})

    def test_exec_form_kiro_hooks_preserve_foreign_args(self):
        self.put(".dotfiles/kiro/hooks/machine.py", "pass\n")
        desired = {"command": "python3", "args": ["~/.kiro/hooks/machine.py", "new"]}
        foreign = {"command": "python3", "args": ["~/.kiro/hooks/vibemon.py", "stop"]}
        stale = {"command": "python3", "args": [str(self.home / ".kiro/hooks/machine.py"), "old"]}
        self.put(".dotfiles/kiro/agents/default.json", json.dumps({"hooks": {"stop": [desired]}}))
        target = self.put(".kiro/agents/default.json", json.dumps({"hooks": {"stop": [foreign, stale]}}))
        self.sync()
        self.assertEqual(json.loads(target.read_text())["hooks"]["stop"], [foreign, desired])

    def test_machine_hooks_are_registered_in_empty_event(self):
        desired = self.configure_machine_hooks()
        target = self.put(".claude/settings.json", '{"hooks":{"SessionStart":[]}}')
        self.sync()
        self.assertEqual(json.loads(target.read_text())["hooks"]["SessionStart"], [desired])

    def test_removed_machine_script_registration_is_pruned_with_file(self):
        self.configure_machine_hooks()
        self.sync()
        (self.repo / "claude/hooks/machine.sh").unlink()
        self.put(".dotfiles/claude/settings.json", '{"hooks": {}}')
        self.sync()
        self.assertEqual(json.loads((self.home / ".claude/settings.json").read_text())["hooks"], {})
        self.assertFalse((self.home / ".claude/hooks/machine.sh").exists())

    def test_memory_sync_removal_preserves_other_hooks_and_memory(self):
        self.put(".dotfiles/claude/settings.json", (ROOT / "claude/settings.json").read_text())
        script = self.put(".claude/hooks/memory-sync.sh", "#!/bin/bash\nexit 0\n")
        manifest = self.put(".toast/vibe_manifest_claude", "hooks/memory-sync.sh\nsettings.json\n")
        foreign = {"type": "command", "command": "python3 ~/.claude/hooks/vibemon.py"}
        custom = {"type": "command", "command": "romty hook claude"}
        target = self.put(".claude/settings.json", json.dumps({"custom": False, "hooks": {
            "SessionStart": [{"matcher": "startup", "hooks": [foreign,
                self.machine_hook('bash "${HOME}/.claude/hooks/memory-sync.sh" start')]}],
            "SessionEnd": [{"hooks": [self.machine_hook("bash ~/.claude/hooks/memory-sync.sh end")]}],
            "Stop": [{"hooks": [custom]}]}}))
        memory = self.put(".claude-memory/workspace/project/MEMORY.md", "existing memory\n")
        link = self.home / ".claude/projects/project/memory"
        link.parent.mkdir(parents=True)
        link.symlink_to(memory.parent, target_is_directory=True)

        self.sync()

        settings = json.loads(target.read_text())
        self.assertFalse(settings["custom"])
        self.assertEqual(settings["hooks"], {
            "SessionStart": [{"matcher": "startup", "hooks": [foreign]}],
            "Stop": [{"hooks": [custom]}]})
        self.assertFalse(script.exists())
        backup = script.with_name(script.name + ".backup")
        self.assertEqual(backup.read_text(), "#!/bin/bash\nexit 0\n")
        self.assertEqual(backup.stat().st_mode & 0o777, 0o600)
        self.assertNotIn("hooks/memory-sync.sh", manifest.read_text().splitlines())
        self.assertTrue(link.is_symlink())
        self.assertEqual((link / "MEMORY.md").read_text(), "existing memory\n")
        first = target.read_bytes(), target.stat().st_mtime_ns
        self.sync()
        self.assertEqual((target.read_bytes(), target.stat().st_mtime_ns), first)
        self.assertEqual(memory.read_text(), "existing memory\n")

    def test_vibemon_files_are_released_without_overwrite_or_prune(self):
        for tool, relative in (("claude", "statusline.py"), ("claude", "hooks/vibemon.py"),
                               ("codex", "hooks/vibemon.py"), ("kiro", "hooks/vibemon.py"),
                               ("kiro", "hooks/vibemon.json")):
            self.put(f".{tool}/{relative}", "current VibeMon payload\n")
            self.put(f".dotfiles/{tool}/{relative}", "obsolete copy\n")
            manifest = self.home / f".toast/vibe_manifest_{tool}"
            manifest.parent.mkdir(exist_ok=True)
            with manifest.open("a") as stream:
                stream.write(relative + "\n")
        self.sync()
        for tool in ("claude", "codex", "kiro"):
            self.assertNotIn("vibemon", (self.home / f".toast/vibe_manifest_{tool}").read_text())
            path = self.home / f".{tool}/hooks/vibemon.py"
            self.assertEqual(path.read_text(), "current VibeMon payload\n")
            self.assertFalse(path.with_suffix(".py.backup").exists())
            (self.repo / tool / "hooks/vibemon.py").unlink()
        self.sync()
        self.assertEqual((self.home / ".claude/statusline.py").read_text(), "current VibeMon payload\n")

    def test_removed_shared_config_is_released_without_deleting_foreign_settings(self):
        self.sync()
        path = self.put(".codex/hooks.json", '{"hooks":{"Stop":[{"hooks":[{"command":"romty hook codex"}]}]}}')
        original = path.read_bytes()
        (self.repo / "codex/hooks.json").unlink()
        self.sync()
        self.assertEqual(path.read_bytes(), original)
        self.assertNotIn("hooks.json", (self.home / ".toast/vibe_manifest_codex").read_text())

    def test_malformed_hook_map_fails_without_writes(self):
        self.configure_machine_hooks()
        target = self.put(".claude/settings.json", '{"hooks":{"SessionStart":false}}')
        self.sync(ok=False)
        self.assertEqual(target.read_text(), '{"hooks":{"SessionStart":false}}')
        self.assertFalse((self.home / ".claude/hooks/machine.sh").exists())

    def test_claude_deny_rules_follow_repository(self):
        self.put(".dotfiles/claude/settings.json", '{"permissions":{"allow":["WebFetch"],"deny":["Bash(sh)"]}}\n')
        target = self.put(".claude/settings.json",
                          '{"permissions":{"allow":["Read"],"deny":["Bash(curl * | sh:*)"],"defaultMode":"plan"}}\n')
        self.sync()
        self.assertEqual(json.loads(target.read_text()),
                         {"permissions":{"allow":["Read"],"deny":["Bash(sh)"],"defaultMode":"plan"}})
        self.assertIn("curl", target.with_name("settings.json.backup").read_text())
        self.assertNotIn("SYNC: ~/.claude/settings.json", self.sync().stdout)

    def test_claude_auto_mode_follows_repository(self):
        self.put(".dotfiles/claude/settings.json", '{"autoMode":{"environment":["repo"],"soft_deny":["$defaults"]}}\n')
        target = self.put(".claude/settings.json", '{"autoMode":{"environment":["stale"],"soft_deny":["local"]},"theme":"auto"}\n')
        self.sync()
        self.assertEqual(json.loads(target.read_text()),
                         {"autoMode":{"environment":["repo"],"soft_deny":["$defaults"]},"theme":"auto"})

    def test_claude_local_deny_rules_stay_without_repository_list(self):
        self.put(".dotfiles/claude/settings.json", '{"permissions":{"allow":["WebFetch"]}}\n')
        target = self.put(".claude/settings.json", '{"permissions":{"deny":["Bash(local)"]}}\n')
        self.sync()
        self.assertEqual(json.loads(target.read_text()), {"permissions":{"allow":["WebFetch"],"deny":["Bash(local)"]}})

    def test_codex_permission_profile_replaces_local_policy_and_legacy_sandbox(self):
        self.put(".dotfiles/codex/config.toml", 'approval_policy = "never"\ndefault_permissions = ":danger-full-access"\n[features]\nhooks = true\n')
        original = '''# Machine preferences
approval_policy = "on-request"
approvals_reviewer = "auto_review"
default_permissions = "git-write"
sandbox_mode = "workspace-write"
model = "local-model"
[sandbox_workspace_write]
network_access = false
writable_roots = [
    "/local/cache",
]
[features]
hooks = false
[mcp_servers.local]
command = "local-mcp"
[projects."/local/project"]
trust_level = "trusted"
'''
        target = self.put(".codex/config.toml", original)
        self.sync()
        expected = tomllib.loads(original)
        expected.update(approval_policy="never", default_permissions=":danger-full-access")
        for key in ("approvals_reviewer", "sandbox_mode", "sandbox_workspace_write"):
            del expected[key]
        self.assertEqual(tomllib.loads(target.read_text()), expected)
        backup = target.with_name(target.name + ".backup")
        self.assertEqual(backup.read_text(), original)
        self.assertEqual(backup.stat().st_mode & 0o777, 0o600)
        first = target.read_bytes()
        stamp = target.stat().st_mtime_ns
        self.sync()
        self.assertEqual(target.read_bytes(), first)
        self.assertEqual(target.stat().st_mtime_ns, stamp)
        self.assertEqual(backup.read_text(), original)

    def test_codex_permission_tables_and_multiline_local_values(self):
        self.put(".dotfiles/codex/config.toml", 'approval_policy = "never"\ndefault_permissions = ":danger-full-access"\n[features]\nhooks = true\n')
        original = '''custom_instructions = """
[approval_policy.granular]
rules = true
[features]
"""
sandbox_workspace_write.network_access = false
[approval_policy.granular]
rules = true
request_permissions = true
[features]
hooks = false
[[examples]]
name = "preserved array of tables"
[tui]
status_line = [
    "model-with-reasoning",
    "git-branch",
]
'''
        target = self.put(".codex/config.toml", original)
        self.sync()
        expected = tomllib.loads(original)
        expected.update(approval_policy="never", default_permissions=":danger-full-access")
        del expected["sandbox_workspace_write"]
        self.assertEqual(tomllib.loads(target.read_text()), expected)
        first = target.read_bytes()
        self.sync()
        self.assertEqual(target.read_bytes(), first)

    def test_codex_repository_can_select_a_different_permission_profile(self):
        self.put(".dotfiles/codex/config.toml", 'approval_policy = "on-request"\napprovals_reviewer = "auto_review"\ndefault_permissions = "work"\n[permissions.work]\nextends = ":workspace"\n')
        target = self.put(".codex/config.toml", 'approval_policy = "never"\ndefault_permissions = ":danger-full-access"\nmodel = "local-model"\n[permissions.personal]\nextends = ":read-only"\n')
        self.sync()
        config = tomllib.loads(target.read_text())
        self.assertEqual(config["approval_policy"], "on-request")
        self.assertEqual(config["approvals_reviewer"], "auto_review")
        self.assertEqual(config["default_permissions"], "work")
        self.assertEqual(config["model"], "local-model")
        self.assertEqual(config["permissions"], {"work": {"extends": ":workspace"},
                                                "personal": {"extends": ":read-only"}})

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
        for name, _ in (("claude", ".claude"), ("codex", ".codex"), ("kiro", ".kiro"), ("opencode", ".config/opencode")):
            if (self.repo / name).exists():
                shutil.rmtree(self.repo / name)
            shutil.copytree(ROOT / name, self.repo / name)
        self.sync()
        self.sync()
        for source_name, destination in (("claude", ".claude"), ("codex", ".codex"), ("codex/skills", ".agents/skills"),
                                         ("opencode", ".config/opencode")):
            for source in (self.repo / source_name).rglob("*.md"):
                relative = source.relative_to(self.repo / source_name)
                if source_name == "codex" and relative.parts[0] == "skills":
                    continue
                self.assertEqual(source.read_bytes(), (self.home / destination / relative).read_bytes())
        self.assertEqual(tomllib.loads((self.repo / "codex/config.toml").read_text()),
                         tomllib.loads((self.home / ".codex/config.toml").read_text()))

    def test_opencode_sync_keeps_machine_config(self):
        self.put(".dotfiles/opencode/agents/reviewer.md", "reviewer\n")
        config = self.put(".config/opencode/opencode.jsonc", '{"providers": {"local": {"apiKey": "secret"}}}\n')
        plugin = self.put(".config/opencode/plugins/vibemon.js", "plugin\n")
        self.sync()
        self.assertEqual((self.home / ".config/opencode/AGENTS.md").read_text(), "shared OpenCode instructions\n")
        (self.repo / "opencode/agents/reviewer.md").unlink()
        self.sync()
        self.assertFalse((self.home / ".config/opencode/agents/reviewer.md").exists())
        self.assertEqual(config.read_text(), '{"providers": {"local": {"apiKey": "secret"}}}\n')
        self.assertEqual(plugin.read_text(), "plugin\n")
        self.assertFalse(config.with_name("opencode.jsonc.backup").exists())

    def test_opencode_permissions_follow_repository(self):
        rules = [{"action": "shell", "resource": "reboot *", "effect": "deny"}]
        self.put(".dotfiles/opencode/opencode.json", json.dumps({"permissions": rules}))
        local = {"model": "local/model", "permissions": [{"action": "shell", "resource": "old *", "effect": "deny"}]}
        target = self.put(".config/opencode/opencode.json", json.dumps(local))
        self.sync()
        self.assertEqual(json.loads(target.read_text()), {"model": "local/model", "permissions": rules})
        self.assertEqual(json.loads(target.with_name("opencode.json.backup").read_text()), local)
        (self.repo / "opencode/opencode.json").unlink()
        self.sync()
        self.assertTrue(target.exists())

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
            # macOS temporary paths can use /var aliases for /private/var.
            if Path(destination).resolve() == target.resolve():
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
        self.module = runpy.run_path(str(ROOT / "scripts/gen-ai-tools.py"))
        self.sources = self.module["Sources"](["validate"], {"git-workflow": "Git Workflow"})

    def fixture(self):
        """Copy the generator, its sources, and committed outputs into a temporary repository."""
        temp = tempfile.TemporaryDirectory(prefix="dotfiles-generator-")
        self.addCleanup(temp.cleanup)
        fixture = Path(temp.name)
        shutil.copytree(ROOT / "scripts", fixture / "scripts", ignore=shutil.ignore_patterns("__pycache__"))
        for name in ("claude", "codex", "opencode"):
            shutil.copytree(ROOT / name, fixture / name)
        return fixture

    def generate(self, fixture, *args):
        return subprocess.run([sys.executable, str(fixture / "scripts/gen-ai-tools.py"), *args],
                              capture_output=True, text=True)

    def test_multiline_frontmatter_is_removed(self):
        source = "---\nname: example\nallowed-tools:\n  - Read\n  - Bash\ndescription: example\n---\nbody\n"
        expected = "---\nname: example\ndescription: example\n---\nbody\n"
        self.assertEqual(self.module["strip_frontmatter"](source, ("allowed-tools",)), expected)

    def test_tool_specific_instructions_and_project_names(self):
        transform = self.module["transform"]
        source = "---\nname: sample\ndescription: sample\ndisable-model-invocation: true\n---\n"
        source += "CLAUDE.md / AGENTS.md\n`rules/git-workflow.md`\n`/validate`\nskills/validate/SKILL.md\n"
        source += "PR 번호 인자: `$ARGUMENTS`\n"
        codex = transform(source, self.module["CODEX_TOOL"], self.sources)
        opencode = transform(source, self.module["OPENCODE_TOOL"], self.sources)
        self.assertNotIn("disable-model-invocation:", codex)
        self.assertIn("disable-model-invocation: true", opencode)
        for result, invocation in ((codex, "`$validate`"), (opencode, "`@validate`")):
            self.assertNotIn("rules/git-workflow.md", result)
            self.assertNotIn("$ARGUMENTS", result)
            self.assertIn("CLAUDE.md / AGENTS.md", result)
            self.assertIn("AGENTS.md의 Git Workflow", result)
            self.assertIn(invocation, result)
            self.assertIn("skills/validate/SKILL.md", result)
        with self.assertRaises(ValueError):
            transform("`rules/missing.md`", self.module["CODEX_TOOL"], self.sources)

    def test_claude_deny_rules_become_shell_patterns(self):
        fixture = self.fixture()
        settings = {"permissions": {"deny": ["Bash(reboot:*)", "Bash(sh)", "Bash(chown -R * /)"]}}
        (fixture / "claude/settings.json").write_text(json.dumps(settings))
        self.assertEqual(self.generate(fixture).returncode, 0)
        config = json.loads((fixture / "opencode/opencode.json").read_text())
        self.assertEqual([rule["resource"] for rule in config["permissions"]], ["reboot *", "sh", "chown -R * /"])
        self.assertTrue(all(rule["action"] == "shell" and rule["effect"] == "deny" for rule in config["permissions"]))
        settings["permissions"]["deny"].append("Read(./secret)")
        (fixture / "claude/settings.json").write_text(json.dumps(settings))
        result = self.generate(fixture)
        self.assertEqual(result.returncode, 1)
        self.assertIn("Read(./secret)", result.stderr)

    def test_agent_tools_become_permission_allowlist(self):
        with tempfile.TemporaryDirectory(prefix="dotfiles-agent-") as tmp:
            agent = Path(tmp) / "reviewer.md"
            agent.write_text("---\nname: reviewer\ndescription: Review; see /validate\ntools: Read, Bash\n---\n\nBody\n")
            result = self.module["convert_agent"](agent, self.sources, ["reboot *"])
            self.assertTrue(result.startswith('---\ndescription: "Review; see @validate"\nmode: subagent\n'))
            rules = re.findall(r'action: "([^"]+)", resource: "([^"]+)", effect: "(\w+)"', result)
            self.assertEqual(rules[0], ("*", "*", "deny"))
            self.assertNotIn(("edit", "*", "allow"), rules)
            # OpenCode applies the last matching rule: guards must follow the allowances they protect.
            self.assertLess(rules.index(("read", "*", "allow")), rules.index(("read", "*.env", "ask")))
            self.assertLess(rules.index(("shell", "*", "allow")), rules.index(("shell", "reboot *", "deny")))
            self.assertTrue(result.endswith("---\n\nBody\n"))
            for frontmatter in ("name: other\ndescription: x\ntools: Read", "name: reviewer\ndescription: x\ntools: Task",
                                "name: reviewer\ndescription: x\ntools: Read\nmodel: opus"):
                agent.write_text(f"---\n{frontmatter}\n---\nBody\n")
                with self.subTest(frontmatter=frontmatter), self.assertRaises(ValueError):
                    self.module["convert_agent"](agent, self.sources, [])

    def test_committed_files_are_current(self):
        result = subprocess.run(
            [sys.executable, str(ROOT / "scripts/gen-ai-tools.py"), "--check"],
            capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_stale_files_and_deleted_sources(self):
        fixture = self.fixture()
        metadata = {p: p.read_bytes() for p in (fixture / "codex/skills").rglob("*.yaml")}
        stale = [fixture / tool / "skills/nextjs-init/references/setup.md" for tool in ("codex", "opencode")]
        (fixture / "claude/skills/nextjs-init/references/setup.md").unlink()
        shutil.rmtree(fixture / "claude/skills/commit")
        (fixture / "claude/agents/debugger.md").unlink()
        self.assertNotEqual(self.generate(fixture, "--check").returncode, 0)
        self.assertTrue(all(path.exists() for path in stale))
        result = self.generate(fixture)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertFalse(any(path.exists() for path in stale))
        self.assertFalse((fixture / "codex/skills/commit/SKILL.md").exists())
        self.assertFalse((fixture / "opencode/skills/commit").exists())
        self.assertFalse((fixture / "opencode/agents/debugger.md").exists())
        self.assertTrue(all(p.read_bytes() == data for p, data in metadata.items()))
        self.assertEqual(self.generate(fixture, "--check").returncode, 0)

    def test_changed_claude_instructions_fail_loudly(self):
        fixture = self.fixture()
        (fixture / "claude/CLAUDE.md").write_text("# CLAUDE.md\n")
        before = (fixture / "codex/AGENTS.md").read_bytes()
        result = self.generate(fixture)
        self.assertEqual(result.returncode, 1)
        self.assertIn("claude/CLAUDE.md no longer contains", result.stderr)
        self.assertEqual((fixture / "codex/AGENTS.md").read_bytes(), before)


class SkillReferenceTests(unittest.TestCase):
    def test_referenced_files_exist(self):
        for tool in ("claude", "codex", "opencode"):
            root = ROOT / tool
            for source in root.rglob("*.md"):
                body = source.read_text()
                references = [
                    root / match
                    for match in re.findall(r"`((?:skills|rules)/[\w./-]+\.md)(?:#[^`]+)?`", body)
                ]
                references += [
                    source.parent / match
                    for match in re.findall(r"\]\(([^():#\s]+\.md)(?:#[^)]*)?\)", body)
                ]
                for target in references:
                    with self.subTest(source=source.relative_to(ROOT), target=target):
                        self.assertTrue(target.is_file(), f"Missing reference: {target}")


if __name__ == "__main__":
    unittest.main()
