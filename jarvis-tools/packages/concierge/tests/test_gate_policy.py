"""Gate locality and the backend-permission policy helpers (issue #8).

`local` separates doing (checkable in the workspace) from publishing (crosses
the machine boundary); compositions derive it (AllOf=all, AnyOf=any). The
policy helpers turn that into "which non-local parts can't the harness publish"
and "does this backend/gate pair make sense".
"""
from concierge import backends, gates
from concierge.backends import claude, codex
from concierge.gates import Always, FileExists, Gate, PrMerged, PrOpen, ShellOk


# -- leaf locality --

def test_local_leaves():
    assert Always().local is True
    assert FileExists("report.md").local is True
    assert ShellOk("pytest -q").local is True
    # crossing the machine boundary → not local
    assert PrOpen().local is False
    assert PrMerged().local is False


def test_publishable_leaves():
    # only PrOpen is publishable by the harness (push branch + open PR);
    # PrMerged is not — the harness opens PRs, never merges
    assert PrOpen().publishable is True
    assert PrMerged().publishable is False
    assert ShellOk("x").publishable is False
    assert FileExists("x").publishable is False
    assert Always().publishable is False


# -- composition locality: AllOf=all, AnyOf=any --

def test_allof_local_is_all():
    assert (ShellOk("a") & FileExists("b")).local is True            # all local
    assert (ShellOk("a") & PrOpen()).local is False                  # one non-local
    assert (PrOpen() & PrMerged()).local is False


def test_anyof_local_is_any():
    assert (ShellOk("a") | FileExists("b")).local is True            # both local
    assert (ShellOk("a") | PrOpen()).local is True                   # one local branch is enough
    assert (PrOpen() | PrMerged()).local is False                    # no local branch


def test_nested_composition_locality():
    # (ShellOk AND PrOpen) OR FileExists  → the OR has a fully-local branch
    g = (ShellOk("a") & PrOpen()) | FileExists("b")
    assert g.local is True
    # (ShellOk OR PrOpen) AND PrMerged → the AND drags it non-local
    g2 = (ShellOk("a") | PrOpen()) & PrMerged()
    assert g2.local is False


# -- leaves() flattening --

def test_leaves_flattens_nested():
    g = (ShellOk("a") & PrOpen()) | (FileExists("b") & PrMerged())
    kinds = sorted(leaf.kind for leaf in g.leaves())
    assert kinds == ["file_exists", "pr_merged", "pr_open", "shell_ok"]
    assert ShellOk("a").leaves() == [ShellOk("a")]  # a leaf is itself


# -- without_publishable(): the LOCAL-only projection --

def test_without_publishable_masks_pr_open():
    g = ShellOk("a") & PrOpen()
    projected = g.without_publishable()
    # PrOpen replaced by Always → the projection is fully local
    assert projected.local is True
    assert not any(isinstance(leaf, PrOpen) for leaf in projected.leaves())
    assert any(isinstance(leaf, ShellOk) for leaf in projected.leaves())
    # PrMerged is NOT publishable, so it survives the projection
    g2 = ShellOk("a") & PrMerged()
    assert g2.without_publishable().local is False


# -- policy helpers --

def test_unpublishable_nonlocal():
    assert gates.unpublishable_nonlocal(ShellOk("a")) == []
    assert gates.unpublishable_nonlocal(PrOpen()) == []               # publishable → coverable
    bad = gates.unpublishable_nonlocal(ShellOk("a") & PrMerged())
    assert [g.kind for g in bad] == ["pr_merged"]


def test_wants_publish():
    assert gates.wants_publish(PrOpen()) is True
    assert gates.wants_publish(ShellOk("a") & PrOpen()) is True
    assert gates.wants_publish(ShellOk("a")) is False
    assert gates.wants_publish(PrMerged()) is False                   # not publishable


def test_backend_gate_mismatch():
    # codex + local gate: fine
    assert gates.backend_gate_mismatch(ShellOk("a"), "codex") is None
    # codex + PrOpen: fine (harness publishes)
    assert gates.backend_gate_mismatch(PrOpen(), "codex") is None
    assert gates.backend_gate_mismatch(ShellOk("a") & PrOpen(), "codex") is None
    # codex + PrMerged: rejected, message points at claude
    msg = gates.backend_gate_mismatch(PrMerged(), "codex")
    assert msg and "claude" in msg and "pr_merged" in msg
    # claude can push, so any gate is fine
    assert gates.backend_gate_mismatch(PrMerged(), "claude") is None
    assert gates.backend_gate_mismatch(PrMerged(), None) is None      # None → default claude


# -- backend capability lives with the module --

def test_can_push_sources_from_backend_module():
    assert claude.CAN_PUSH is True
    assert codex.CAN_PUSH is False
    assert backends.can_push("claude") is True
    assert backends.can_push("codex") is False
    assert backends.can_push(None) is True          # default (claude)
    # the __init__ helper mirrors the module constants exactly
    assert backends.can_push("claude") == claude.CAN_PUSH
    assert backends.can_push("codex") == codex.CAN_PUSH


# -- serialization is unaffected by the added properties --

def test_locality_survives_json_roundtrip():
    g = ShellOk("pytest") & PrOpen()
    g2 = Gate.from_json(g.to_json())
    assert g2.local == g.local
    assert gates.wants_publish(g2) is True
