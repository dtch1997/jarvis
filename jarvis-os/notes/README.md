# notes/

Atomic living-state notes — current truth about ongoing research, distilled from sources.

Conventions (see DESIGN.md "memory layer"):
- One note per stable concept. Updates patch the relevant note in place.
- Frontmatter: `source` (where this came from), `last_synced` (when the source was last read). Stale notes get flagged before use, not silently trusted.
- Raw source snapshots live in `sources/` for delta-reading on re-sync.
- What changed per sync goes in `changelog.md` (append-only) — "what's new" is a different artifact from "what's true".
- Human edits win: a sync must never clobber a human-edited note; propose a diff instead.
