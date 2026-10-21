"""Apply bounded serving fixes to the pinned TensorFold package at image build time."""

import hashlib
import importlib.util
from pathlib import Path
import shutil


def replace_once(path: Path, before: str, after: str) -> None:
    source = path.read_text()
    if source.count(before) != 1:
        raise SystemExit(f"Pinned TensorFold patch no longer matches: {path.name}")
    source = source.replace(before, after, 1)
    compile(source, str(path), "exec")
    path.write_text(source)


root = Path(importlib.util.find_spec("tensorfold").origin).parent
path = root / "families/qwen4_exp/__init__.py"
source = path.read_text()
original = 'vision_urls=bool(options.get("vision_urls", False)))'
replacement = ('vision_urls=bool(options.get("vision_urls", False)),\n'
               '                           draft_vocab=os.environ.get("TENSORFOLD_DRAFT_VOCAB_PATH", "default"))')
if source.count(original) != 1 or source.count("from pathlib import Path") != 1:
    raise SystemExit("Pinned TensorFold vocabulary hook no longer matches")
source = source.replace("from pathlib import Path", "import os\nfrom pathlib import Path", 1)
source = source.replace(original, replacement, 1)
compile(source, str(path), "exec")
path.write_text(source)

assets = Path(__file__).resolve().parent / "tensorfold"
prefixes = root / "families/qwen4_exp/cuda/prefixes.py"
if hashlib.sha256(prefixes.read_bytes().rstrip() + b"\n").hexdigest() != "b6b0208a44b6ad22b947a6b428dba6d01eaf59cfcb46201c8827cbec0a781e2e":
    raise SystemExit("Pinned TensorFold prefix selector no longer matches")
shutil.copyfile(assets / "prefixes.py", prefixes)

multi = root / "families/qwen4_exp/cuda/multi.py"
replace_once(multi,
             'if any(not x.done and not x.waiting for x in self.streams.values()) or self.arrived():',
             'if ended or any(not x.done and not x.waiting for x in self.streams.values()) or self.arrived():')
replace_once(multi,
             'ended += self._fill()                      # passes alone; a prompt that ends here joins this round\n',
             'ended += self._fill()                      # passes alone; a prompt that ends here joins this round\n'
             '            if ended:                             # release completed replies before another GPU pass\n'
             '                return ended\n')

shutil.copyfile(assets / "observability.py", root / "cuda/dockpad_observability.py")
shutil.copyfile(assets / "policy.py", root / "cuda/dockpad_policy.py")
server = root / "cuda/server.py"
replace_once(server, 'from tensorfold.cuda import health',
             'from tensorfold.cuda.dockpad_observability import observe_request\n'
             'from tensorfold.cuda.dockpad_policy import thinking_budget\nfrom tensorfold.cuda import health')
replace_once(server,
             'budget = int(budget or getattr(self, "thinking_budget", 0)) if chat and thinking else 0     # 0: the default',
             'budget = thinking_budget(budget, getattr(self, "thinking_budget", 0), max_tokens, chat and thinking)')
replace_once(server, '    def run(self, body:', '    @observe_request\n    def run(self, body:')
metrics = root / "server/metrics.py"
replace_once(metrics, '    return "\\n".join(lines) + "\\n"',
             '    from tensorfold.cuda.dockpad_observability import render_observations\n'
             '    return "\\n".join(lines) + "\\n" + render_observations(app)')
