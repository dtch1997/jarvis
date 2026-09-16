import sys, types, re
from pathlib import Path
REPO = "/mnt/nw/home/d.tan/jarvis-monorepo/repos/sam-rl-rewardhacks"
# stub the heavy/unneeded imports run_probe pulls in at import time
for name in ["chz", "dotenv", "lib.sample", "run_aisi_ckpt_beliefs"]:
    m = types.ModuleType(name); sys.modules[name] = m
sys.modules["chz"].chz = lambda cls=None, **kw: (cls if cls else (lambda c: c))
sys.modules["dotenv"].load_dotenv = lambda *a, **k: None
for n in ["flush_cost", "make_client", "sample_all"]: setattr(sys.modules["lib.sample"], n, None)
for n in ["SUFFIX", "gut_pyes", "parse_answer"]: setattr(sys.modules["run_aisi_ckpt_beliefs"], n, None)
import ast
ad = types.ModuleType("lib.aisi_data"); sys.modules["lib.aisi_data"] = ad
tree = ast.parse(Path(REPO, "lib/aisi_data.py").read_text())
for node in tree.body:
    if isinstance(node, ast.Assign) and any(getattr(t, "id", None) == "USER_NOTE_PREFIX" for t in node.targets):
        exec(compile(ast.Module([node], []), "aisi_data", "exec"), ad.__dict__)

sys.path.insert(0, REPO)
src = Path(REPO, "reward_awareness/build_introspect_viewer.py").read_text().replace("/workspace/rl-monitor-evasion", REPO)
rp = Path(REPO, "reward_awareness/run_probe.py").read_text().replace("/workspace/rl-monitor-evasion", REPO)
# make run_probe importable under the stubbed deps
mod = types.ModuleType("reward_awareness.run_probe"); mod.__file__ = str(Path(REPO, "reward_awareness/run_probe.py"))
pkg = types.ModuleType("reward_awareness"); pkg.__path__ = [str(Path(REPO, "reward_awareness"))]; sys.modules["reward_awareness"] = pkg
# chz.chz decorates a class with fields; keep the class body runnable by executing only up to the Cfg definition
cut = rp.index("@chz.chz")
exec(compile(rp[:cut], mod.__file__, "exec"), mod.__dict__)
import itertools; mod.ORDERS = list(itertools.permutations(range(3)))
sys.modules["reward_awareness.run_probe"] = mod
sys.argv = ["build", sys.argv[1]]
exec(compile(src, "build_introspect_viewer.py", "exec"), {"__name__": "__main__"})
