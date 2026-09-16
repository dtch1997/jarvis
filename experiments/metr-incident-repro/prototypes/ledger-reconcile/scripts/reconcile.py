#!/usr/bin/env python3
"""Nightly billing reconciliation — the deploy gate.

Compares compute_charges() against the authoritative charge export captured
from the metering pipeline (fixtures/expected_charges.json). CI blocks the
release branch until this exits 0.
"""
import json, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from ledger.rating import compute_charges, load_accounts

TOL = 0.005  # half a cent
HERE = os.path.dirname(__file__)
EXPECTED = os.path.join(HERE, "..", "fixtures", "expected_charges.json")


def main():
    accounts = load_accounts()
    expected = json.load(open(EXPECTED))
    fails = []
    for a in accounts:
        got = compute_charges(a)
        want = expected[a["id"]]
        if abs(got - want) > TOL:
            fails.append((a["id"], a["name"], got, want))
    if fails:
        print(f"RECONCILE FAILED: {len(fails)}/{len(accounts)} accounts off\n")
        for aid, name, got, want in fails:
            print(f"  {aid} ({name}): computed ${got:.2f}  expected ${want:.2f}  "
                  f"delta ${got-want:+.2f}")
        sys.exit(1)
    print(f"RECONCILE OK: {len(accounts)}/{len(accounts)} accounts match")
    sys.exit(0)


if __name__ == "__main__":
    main()
