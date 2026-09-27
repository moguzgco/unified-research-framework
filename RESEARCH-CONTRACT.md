# URF Research Contract

Runtime contract shared by every URF research project. A private project holds a read-only copy at `framework/RESEARCH-CONTRACT.md`. Design rationale lives in `URF_ARCHITECTURE.md`, which is not loaded at runtime.

## 1. Files and load order

Each run reads, in this order:

1. `framework/RESEARCH-CONTRACT.md` (this file).
2. `framework/FRAMEWORK.md` and `framework/SOURCES.md`.
3. `PROJECT.md` and, if present, `SOURCES.md`.
4. `state.json`.
5. The most recent daily report; on a synthesis day, every daily report of the period.
6. Only the `framework/sources/*.md` guides for sources used in this run.

Files in `framework/` are read-only for the research agent. The research agent writes only `state.json` and `reports/`.

Optional context reuse: previously loaded instructions may be reused only when the agent can confirm the files are unchanged (for example, the same Git commit for those paths). `state.json` and the reports needed for the run are always read fresh. When in doubt, reload. Correct execution never depends on retained context.

## 2. Precedence

For configurable settings (sources, budgets, procedures, reporting preferences):

`PROJECT.md` / `SOURCES.md` > `framework/FRAMEWORK.md` / `framework/SOURCES.md` > defaults in this contract.

An explicit project value is an override even when it equals the parent value. At the same layer, an explicit exclusion wins over an inclusion; note the inconsistency in the report. The invariants in section 3 are not configurable.

## 3. Invariants

No framework or project setting may disable or weaken these.

- **I1 Evidence.** Every reported finding links to at least one source the agent actually accessed. Verify against original sources as the framework requires. Anything not verified is reported as an unverified lead, not a finding.
- **I2 Truthful reporting.** Report actual coverage, failures and partial runs. Never pad findings or claim checks that were not performed.
- **I3 Genuine dates.** Reports and state use the actual execution date. Never backdate or fabricate a dated report.
- **I4 Checkpoints.** Never advance baseline progress or a source checkpoint beyond verified coverage.
- **I5 Continuity.** Never delete historical reports or compact historical identifiers. A failed run leaves the last successful state intact.
- **I6 Persist before notifying.** Send email only after the report and state have been committed and pushed successfully.
- **I7 Source scope.** Never use an effective excluded source for discovery or verification.

## 4. Run type

- **Baseline** — `state.json` `baseline.status` is `not_started` or `in_progress`. Work within the configured baseline window and budget, prioritizing relevant and significant historical items over exhaustive collection. Record progress in `baseline.progress`; set `complete` only when the window is covered. An unfinished baseline continues in the next run.
- **Incremental** — baseline complete. Discover items new since each source's verified coverage, and re-verify recorded items when new evidence appears or their verification interval is due.
- **Source baseline** — a source that is newly in the effective Allowed list receives a limited baseline of its own within the run budget.

## 5. Effective sources

Compute at the start of each run and list the result in the report.

1. **Allowed.** If the project `Allowed` section says `Mode: only`, use the project list alone. Otherwise (`Mode: add`, the default) combine framework and project entries. A missing or empty project section does not erase framework entries.
2. **Excluded.** Combine framework and project exclusions. A project entry in `Allowed` overrides a framework exclusion of the same source; a project exclusion overrides a framework inclusion.
3. Remove effective exclusions from effective Allowed.
4. An empty effective Allowed list means discovery is unrestricted except for exclusions. A nonempty list restricts discovery to those sources.
5. **Verification links.** Following original-source links outside the Allowed list is permitted only when the effective setting is `permitted` (default: `not permitted`). Exclusions still apply.

Changing sources never erases history: disabled sources stop discovery; newly enabled sources get a source baseline.

## 6. Workflow

1. Pull the latest project `main`. Load files as in section 1.
2. Record the execution date, available tools and permissions. If Git push access is unavailable, stop and report; do not research without a way to persist.
3. Determine the run type (section 4) and compute effective sources (section 5).
4. Discover candidates within effective sources and budget.
5. Screen candidates against scope, relevance, `state.json` and the framework's change indicators.
6. Verify relevant candidates against original sources.
7. Analyze relevance and extract the framework's target fields.
8. Compare with previous observations.
9. Classify each item as new, material change, repeated observation or unverified lead, using the framework's identity and change rules.
10. Write the daily report (section 8) and update `state.json` (section 7).
11. On the configured synthesis day, write the periodic report from the period's daily reports.
12. Validate (section 9), commit and push; confirm the push succeeded.
13. If email is configured and a delivery tool is available, send it (section 10).

## 7. state.json

A compact index, not an archive. Evidence and narrative belong in reports and Git history.

```json
{
  "schema_version": 1,
  "last_run": { "date": null, "type": null, "status": null, "report": null },
  "baseline": { "status": "not_started", "window": null, "progress": null },
  "sources": {},
  "items": {},
  "historical_ids": [],
  "pending_leads": []
}
```

- `items` — active items keyed by the framework's stable ID: `first_seen`, `last_seen`, `last_verified`, `status`, `fingerprint` (the framework's change indicators), `report` (path of the report that last described the item), plus framework-defined fields.
- `historical_ids` — compact IDs of items no longer active. Never removed.
- `sources` — optional per-source `checkpoint` and `last_status`, used only when the framework enables per-source checkpoints.
- `pending_leads` — unverified candidates to retry, each with the date first seen. Keep short; drop a lead only with a reason stated in the report.

## 8. Reports

- Daily: `reports/daily/YYYY-MM-DD.md`. A second run on the same date uses `YYYY-MM-DD-2.md`.
- Periodic: `reports/periodic/YYYY-Www.md` (ISO week), produced within the daily run on the configured synthesis day. If a later run finds the period's synthesis missing, it produces it then.

Daily report skeleton (frameworks may add sections):

```markdown
# <Project> — Daily report YYYY-MM-DD

Run: <ISO timestamp> · Type: baseline | incremental · Status: complete | partial | failed

## Coverage
Effective sources and, for each, checked / partial / failed and the window covered.

## New items
## Material changes
## Repeated observations
## Unverified leads
## Issues and limitations
## State changes
```

Each item lists its ID, title, source link(s), relevant dates, a short evidence summary and its classification. Empty sections say "None". Periodic reports synthesize daily reports only, link each finding to its daily report and original source, and add no unverified claims.

## 9. Failures and validation

- **Source failure** — record it under Coverage, do not advance that source's checkpoint, continue with other sources. Status: partial.
- **Budget exhausted** — stop discovery, record what remains uncovered. Status: partial.
- **Fatal error** — write a failed report with the reason; leave `state.json` unchanged except `last_run`; commit and push the report if possible.
- **Before committing** — `state.json` parses and has the core fields; every new or changed item in state appears in the report; every finding has a link; the report date is the execution date.
- **Push failure** — report it in the run output and send no email.

## 10. Persistence and email

- Commit message: `research: YYYY-MM-DD <type> <status>`. Push to `main` and confirm success.
- Email only when configured in `PROJECT.md` and a delivery tool is available, and only after a confirmed push. Content: short summary and the report's repository path or link.
- Never resend automatically. A failed or uncertain delivery is stated in the run's final output as a notification failure, separate from research status. No commit is made solely to record delivery status.
