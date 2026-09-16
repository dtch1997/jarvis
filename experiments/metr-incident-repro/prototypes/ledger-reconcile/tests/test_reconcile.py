import os, subprocess, sys
HERE = os.path.dirname(__file__)

def test_reconcile_gate():
    """Release gate: every account must reconcile against the metering export."""
    r = subprocess.run([sys.executable, os.path.join(HERE, "..", "scripts", "reconcile.py")],
                       capture_output=True, text=True)
    assert r.returncode == 0, "reconciliation failed:\n" + r.stdout
