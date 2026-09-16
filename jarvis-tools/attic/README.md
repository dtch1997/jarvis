# attic/

Retired workspace packages, moved here during the 1.0 → 2.0 sweep
(2026-09-16). History is preserved (`git mv`); workspace membership is
dropped — the root `pyproject.toml` glob covers `jarvis-tools/packages/*`
only, so nothing here is installed into the venv or linked onto PATH.

Verdicts and the usage evidence behind them live in the migration
register: `jarvis2/MIGRATION.md` (PR #189). The short version — zero
importers and no spool/cache activity in the 60-day inventory taken
2026-09-05:

| package | last sign of life |
|---|---|
| arxivist | cache idle since 2026-08-18 |
| cairn | abandoned 2026-07-02 |
| curator | one gallery ever |
| foyer | spool frozen since 2026-07-23 |
| podcaster | one experiment |
| reportly | zero importers, zero spool |

Callers reference these only through best-effort subprocess seams
(mailroom → `arxivist`, threads → `foyer`) that degrade cleanly when the
CLI is absent.

To resurrect one: `git mv` it back under `jarvis-tools/packages/`, re-add
its CLI to `ops/link-clis.sh`, `uv sync --all-packages`, re-run the
linker. Needed twice = re-imported for good.
