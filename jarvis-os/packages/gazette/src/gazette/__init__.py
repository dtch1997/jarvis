"""gazette — consumer-mode PR flow: merge-on-green + nightly versions.

PRs merge as soon as checks are green (hourly ``gazette sweep``); no lane
label is needed. The safety net is versioning, not review: nightly,
``gazette version cut`` tags main as ``vYYYY.MM.DD`` and ``gazette version
deploy`` deploys it to the box, so the running system changes once per
night and any version can be rolled back to with ``gazette version switch
v<date>`` (``switch latest`` resumes nightly tracking). A morning
``gazette notes`` renders patch notes so Daniel reads what happened
instead of reviewing every PR.

The one gate (GitHub label):

- ``requires-approval`` — money, credentials, external-facing actions,
  destructive ops: never cron-merged, waits for Daniel. Legacy
  ``lane:blocked`` is an alias; legacy ``lane:delay`` is retired and
  treated as auto (2026-08-19 rework).

Veto = add the ``veto`` label or request changes on the PR (pre-merge);
post-merge, roll the box back with ``gazette version switch``. Anything
touching credential-like paths is demoted to requires-approval regardless
of label; merges touching behavior-shaping paths (CLAUDE.md, ops/, …) are
annotated in the sweep log and edition.
"""

from __future__ import annotations

from .lanes import Lane, resolve_lane, decide

__all__ = ["Lane", "resolve_lane", "decide"]

__version__ = "0.2.0"
