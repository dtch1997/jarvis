"""Control / canary submission: no-op auditor.

Returns one deliberately vague hypothesis and no cleaned model. Exercises the
full submit->eval->score path (the arch-init Phase-4 canary) and establishes the
floor score a real method must beat. Detection ~0, removal 0.
"""


def audit(organism_dir: str, workdir: str, budget: dict) -> dict:
    return {
        "findings": [
            {"trigger": "unknown", "behavior": "the model may have some unusual behavior"},
        ],
        "removed_model": None,
    }
