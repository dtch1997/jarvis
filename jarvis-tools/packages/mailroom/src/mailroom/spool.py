from __future__ import annotations
import json
from . import config

def load_state() -> dict:
    try: return json.loads(config.state_path().read_text())
    except (OSError, ValueError): return {}

def write_state(state: dict) -> None:
    config.ensure(); config.state_path().write_text(json.dumps(state, indent=2, sort_keys=True))

def path_for(id_: str): return config.thoughts_dir() / f"{id_.replace(':', '_')}.json"
def write(record: dict) -> None:
    config.ensure(); path_for(record["id"]).write_text(json.dumps(record, indent=2, sort_keys=True))
def load_all() -> list[dict]:
    config.ensure(); out=[]
    for p in sorted(config.thoughts_dir().glob("*.json")):
        try: out.append(json.loads(p.read_text()))
        except (OSError, ValueError): pass
    return out
def ids() -> set[str]: return {r.get("id") for r in load_all()}
