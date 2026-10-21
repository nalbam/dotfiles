import configparser
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class VibeMonDeploymentTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.spark = self.root / 'spark'
        (self.spark / 'scripts').mkdir(parents=True)
        shutil.copy2(ROOT / 'stacks/dgx-spark/scripts/setup-vibemon.sh', self.spark / 'scripts/setup-vibemon.sh')
        shutil.copy2(ROOT / 'stacks/dgx-spark/vibemon.env', self.spark / 'vibemon.env')
        self.config = self.root / 'config'
        (self.config / 'vibemon').mkdir(parents=True)
        self.token = 'vm_' + 'a' * 60
        self.secret = self.config / 'vibemon/collector.env'
        self.secret.write_text('VIBEMON_WRITE_TOKEN=' + self.token + '\n')
        self.secret.chmod(0o600)
        self.binary = self.root / 'bin'
        self.binary.mkdir()
        self.log = self.root / 'calls'
        python = self.binary / 'python3'
        python.write_text('''#!REALPY
import json, os, pathlib, sys
args = sys.argv[1:]
if args[:2] == ['-m', 'venv']:
    root = pathlib.Path(args[2]); (root/'bin').mkdir(parents=True, exist_ok=True)
    script = '#!REALPY\\nimport json,os,sys\\nwith open(os.environ["TEST_CALLS"],"a") as f:f.write(json.dumps(sys.argv[1:])+"\\\\n")\\nif sys.argv[1:3] == ["-m","vibemon_collector.health"]:sys.exit(0 if os.environ["TEST_ACK"] == "yes" else 1)\\n'
    (root/'bin/python').write_text(script); (root/'bin/python').chmod(0o755)
    (root/'bin/vibemon-collector').write_text('#!/bin/sh\\nexit 0\\n'); (root/'bin/vibemon-collector').chmod(0o755)
else:
    os.execv('REALPY', ['REALPY', *args])
'''.replace('REALPY', sys.executable))
        python.chmod(0o755)
        for name in ['git', 'nvidia-smi', 'sleep', 'systemctl', 'loginctl', 'hostname']:
            p = self.binary / name
            p.write_text('''#!REALPY
import json, os, sys
if os.path.basename(sys.argv[0]) == 'loginctl': print(os.environ.get('TEST_LINGER', 'yes'))
if os.path.basename(sys.argv[0]) == 'hostname': print('test-host')
with open(os.environ['TEST_CALLS'], 'a') as f:f.write(json.dumps([os.path.basename(sys.argv[0]), *sys.argv[1:]])+'\\n')
'''.replace('REALPY', sys.executable))
            p.chmod(0o755)
        self.env = {**os.environ, 'PATH': str(self.binary) + ':' + os.environ['PATH'],
                    'XDG_CONFIG_HOME': str(self.config), 'XDG_DATA_HOME': str(self.root / 'data'),
                    'XDG_STATE_HOME': str(self.root / 'state'), 'TEST_CALLS': str(self.log), 'TEST_ACK': 'yes'}

    def run_setup(self, **changes):
        return subprocess.run([str(self.spark / 'scripts/setup-vibemon.sh')], env={**self.env, **changes}, capture_output=True, text=True, timeout=20)

    def test_secret_stays_out_of_unit_and_arguments_and_only_collector_restarts(self):
        result = self.run_setup()
        self.assertEqual(result.returncode, 0, result.stderr)
        unit = self.config / 'systemd/user/dockpad-vibemon-collector.service'
        parser = configparser.ConfigParser(interpolation=None)
        parser.read(unit)
        self.assertEqual(parser['Service']['RestartPreventExitStatus'], '2')
        self.assertIn(str(self.secret), parser['Service']['EnvironmentFile'])
        self.assertIn('--memory-type unified', parser['Service']['ExecStart'])
        self.assertIn('--disk', parser['Service']['ExecStart'])
        self.assertIn('/health', parser['Service']['ExecStartPre'])
        for text in [unit.read_text(), self.log.read_text(), result.stdout, result.stderr]:
            self.assertNotIn(self.token, text)
        calls = [json.loads(line) for line in self.log.read_text().splitlines()]
        restarts = [x for x in calls if x[:3] == ['systemctl', '--user', 'restart']]
        self.assertEqual(restarts, [['systemctl', '--user', 'restart', 'dockpad-vibemon-collector.service']])
        self.assertTrue((self.root / 'data/vibemon-collector/current').is_symlink())
        self.assertEqual(self.secret.read_text(), 'VIBEMON_WRITE_TOKEN=' + self.token + '\n')

    def exec_start(self, config=None):
        parser = configparser.ConfigParser(interpolation=None)
        parser.read((config or self.config) / 'systemd/user/dockpad-vibemon-collector.service')
        return parser['Service']['ExecStart']

    def test_source_identity_defaults_to_the_host_name(self):
        result = self.run_setup()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('--source-id "test-host" --name "DGX Spark"', self.exec_start())

    def test_environment_source_identity_wins(self):
        result = self.run_setup(VIBEMON_SOURCE_ID='lab-gpu', VIBEMON_SOURCE_NAME='Lab GPU')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('--source-id "lab-gpu" --name "Lab GPU"', self.exec_start())

    def test_invalid_source_identity_is_rejected(self):
        result = self.run_setup(VIBEMON_SOURCE_ID='bad id')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('Invalid source ID', result.stderr)
        self.assertFalse((self.root / 'data/vibemon-collector').exists())

    def test_running_without_delivery_does_not_report_success(self):
        result = self.run_setup(TEST_ACK='no')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('has not received a Web acknowledgement', result.stderr)
        self.assertNotIn(self.token, result.stderr)

    @unittest.skipUnless(shutil.which('systemd-analyze'), 'systemd-analyze is required')
    def test_generated_unit_passes_native_systemd_validation(self):
        config = self.root / 'config with spaces'
        self.config.rename(config)
        result = self.run_setup(XDG_CONFIG_HOME=str(config))
        self.assertEqual(result.returncode, 0, result.stderr)
        unit = config / 'systemd/user/dockpad-vibemon-collector.service'
        result = subprocess.run(
            ['systemd-analyze', '--user', 'verify', str(unit)],
            env={**self.env, 'XDG_CONFIG_HOME': str(config)},
            capture_output=True, text=True, timeout=20,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        # Invalid EnvironmentFile paths produce a warning with a zero exit code.
        self.assertEqual(result.stderr, '')

    def test_world_readable_credentials_fail_before_installation(self):
        self.secret.chmod(0o644)
        result = self.run_setup()
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse((self.root / 'data/vibemon-collector').exists())
        self.assertNotIn(self.token, result.stderr)

    def test_an_existing_unmanaged_unit_is_preserved(self):
        directory = self.config / 'systemd/user'
        directory.mkdir(parents=True)
        unit = directory / 'dockpad-vibemon-collector.service'
        unit.write_text('unrelated configuration\n')
        result = self.run_setup()
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(unit.read_text(), 'unrelated configuration\n')
        self.assertFalse((self.root / 'data/vibemon-collector').exists())

    def test_lingering_is_required_before_installation(self):
        result = self.run_setup(TEST_LINGER='no')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('Enable user lingering', result.stderr)
        self.assertFalse((self.root / 'data/vibemon-collector').exists())
