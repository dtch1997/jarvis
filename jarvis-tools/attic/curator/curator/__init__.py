"""curator — a claims-and-figures ledger for research results.

Capture every plot at the moment it is made, paired with the claim it
supports and the provenance that produced it:

    import curator

    curator.add(fig, claim="AFT amplifies EM at all scales tested",
                tags=["phase-2"], data="results/em_sweep.jsonl")

Then curate the set in the browser (inline claim editing, keep/cut triage,
gallery + claims views), served through the shared lobby hub:

    viewer = curator.serve("gallery")
    print(viewer.url)

See DESIGN.md for the full rationale and data model.
"""

from .core import Card, Ledger, add, capture_provenance
from .server import Viewer, serve

__all__ = ["add", "serve", "Card", "Ledger", "Viewer", "capture_provenance"]

__version__ = "0.1.0"
