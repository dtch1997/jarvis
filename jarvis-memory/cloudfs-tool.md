---
name: cloudfs-tool
description: RETIRED 2026-07-10 — merged into ferry as ferry.cas; ArcadiaImpact/cloudfs archived
metadata:
  node_type: memory
  type: project
  originSessionId: 7129edd1-7a35-42fb-bc9e-1907732a4d3d
---

**cloudfs — RETIRED, merged into [[ferry-tool]] (2026-07-10).** The
content-addressed (MD5-keyed) GCS file store lives on as `ferry.cas` — same
API (`Client`, `upload/download/exists/delete/uri`), same defaults
(`gs://alignment-team-general-storage/daniel/cloudfs/<md5>`), so existing
stored ids keep resolving. Env vars now `FERRY_CAS_*` (legacy `CLOUDFS_*`
still honored). ArcadiaImpact/cloudfs is ARCHIVED with a retirement note;
clone repos/cloudfs remains. Gotcha that carried over: this box's ADC has no
default project → client falls back to a cosmetic placeholder (fine — object
ops bill the bucket's project).
