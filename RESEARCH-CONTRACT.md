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
- **I4 Coverage.** Never advance a source's coverage beyond the period that is fully checked (section 4).
- **I5 Continuity.** Never delete historical reports or compact historical identifiers. A failed run leaves the last successful state intact.
- **I6 Persist before notifying.** Send email only after the report and state have been committed and pushed successfully.
- **I7 Source scope.** Never use an effective excluded source for discovery or verification.

## 4. Run type and coverage

Each effective source has an entry in `state.json` `sources` (section 7). When discovery is unrestricted, entries are keyed by the discovery methods named in `FRAMEWORK.md` (for example `web-search`). An entry's `covered_through` is the end of the contiguous period, starting at its `from` date, that has been fully checked: every discovery operation the framework requires for that period completed successfully, in this run or through a valid checkpoint, and every result was screened. Relevant candidates not yet verified remain in `pending_leads`; verifying them is not required for coverage.

- **Baseline** — `baseline.status` is `not_started` or `in_progress`. At the first baseline run, fix `baseline.window` as absolute dates: `to` is the execution date and `from` is `to` minus the configured baseline window; every source entry starts at that `from`. Work each source from its coverage toward `window.to` within the budget, prioritizing relevant and significant historical items over exhaustive collection. Set `baseline.status` to `complete` when every source effective at baseline start has `covered_through` on or after `window.to`. An unfinished baseline continues in the next run.
- **Incremental** — baseline complete. Search each source from its `covered_through` to the execution date, so periods left uncovered by partial or failed runs are revisited before coverage advances. Frameworks may define a small overlap. Re-verify recorded items when new evidence appears or their verification interval is due.
- **Source baseline** — a source newly in the effective Allowed list gets an entry with `from` set to the execution date minus the baseline window, and is worked the same way within the run budget.

**Coverage rule.** At the end of a run, advance a source's `covered_through` only to the end of the contiguous period, starting at its current coverage, that this run fully checked. A failed source or a failed run advances nothing. A period counts as fully checked only when every operation it requires has completed, in this run or through a valid checkpoint (section 7); a checkpoint itself never advances coverage.

## 5. Effective sources

Compute at the start of each run and list the result in the report.

1. **Allowed.** If the project `Allowed` section says `Mode: only`, use the project list alone; an empty `Mode: only` list is a configuration error: report it and use the framework list unchanged. Otherwise (`Mode: add`, the default) combine framework and project entries; if the framework list is empty, discovery stays unrestricted and the project entries are always included. A missing or empty project section does not erase framework entries.
2. **Excluded.** Combine framework and project exclusions. A project entry in `Allowed` overrides a framework exclusion of the same source; a project exclusion overrides a framework inclusion.
3. Remove effective exclusions from effective Allowed.
4. An empty effective Allowed list, or the unrestricted case in step 1, means discovery is unrestricted except for exclusions. Otherwise discovery is restricted to the effective Allowed list.
5. **Matching.** An entry covers its domain and all subdomains, or, for a URL, that path and below. When entries overlap, the more specific entry wins; at equal specificity the rules above apply.
6. **Verification links.** Following original-source links outside the Allowed list is permitted only when the effective setting is `permitted` (default: `not permitted`). Exclusions still apply.

Changing sources never erases history: disabled sources stop discovery; newly enabled sources get a source baseline.

## 6. Workflow

1. Pull the latest project `main`. Load files as in section 1.
2. Record the execution date, available tools and permissions. If Git push access is unavailable, stop and report; do not research without a way to persist.
3. Determine the run type and each source's search period (section 4), and compute effective sources (section 5).
4. Discover candidates within effective sources and budget.
5. Screen candidates against scope, relevance, `state.json` and the framework's change indicators.
6. Verify relevant candidates against original sources.
7. Analyze relevance and extract the framework's target fields.
8. Compare with previous observations.
9. Classify each item (section 8), using the framework's identity and change rules; handle reappearing historical IDs as in section 7.
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
  "baseline": { "status": "not_started", "window": { "from": null, "to": null } },
  "sources": {},
  "items": {},
  "historical_ids": {},
  "pending_leads": []
}
```

- `items` — active items keyed by the framework's stable ID: `first_seen`, `last_seen`, `last_verified`, `status`, `fingerprint` (the framework's change indicators), `report` (path of the report that last described the item), plus framework-defined fields.
- `baseline.window` — absolute `from` and `to` dates, fixed at the first baseline run.
- `sources` — one entry per effective source or discovery method: `from`, `covered_through`, `last_status`, and optionally `checkpoint`. Entries of disabled sources are kept.
  - `last_status` — result of the most recent run that worked the source: `complete` (every required operation for the periods worked completed), `partial` (some completed; others incomplete or unattempted) or `failed` (none completed). A source not worked in a run keeps its value.
  - `checkpoint` — optional, defined by the framework: compact progress within the first period not yet covered (for example completed operations, a cursor or a last ID). It never advances `covered_through`. A later run reuses it only under the framework's validity conditions and otherwise repeats the work. Remove it when that period becomes covered or the checkpoint is invalid.
- `historical_ids` — inactive items keyed by ID, each with only `inactive_since`, `fingerprint` and `report`. Never removed.
- **Inactive items.** An item moves from `items` to `historical_ids` when the framework's inactivity criterion is verified; if the framework defines none, items stay active. Report the move under State changes.
- **Reappearance.** When a candidate's ID is in `historical_ids`, verify it and compare its evidence and fingerprint with the stored record, and with its report if needed. Classify it by the framework's criteria as a repeated observation or a material change. Move it back to `items` only when verified evidence shows it active again by the framework's criteria.
- `pending_leads` — unverified candidates to retry, each with the date first seen. A lead may come from a period that is not yet covered (a partial run), provided that period lies within the baseline window or the run's search period. Match candidates to existing leads by stable identifier first, then by name; when an identifier becomes available for a name-only lead, add it to that lead and keep its first-seen date and origin. Keep short; drop a lead only with a reason stated in the report.

## 8. Reports

- Daily: `reports/daily/YYYY-MM-DD.md`. A second run on the same date uses `YYYY-MM-DD-2.md`.
- Periodic: `reports/periodic/YYYY-Www.md`, named by the ISO week of the synthesis day and produced within the daily run on that day. The period is the seven days ending on the synthesis day, including that day's report. If a later run finds the latest period's synthesis missing, it produces it then.

Classifications:

- **New** — not previously recorded; published within the period searched in this run.
- **First observation** — not previously recorded; published before that period, or without a reliable publication date.
- **Material change** — a recorded or historical item whose fingerprint or evidence differs by the framework's material-change criteria.
- **Repeated observation** — a recorded or historical item with no material difference.
- **Unverified lead** — not yet verified.

Daily report skeleton (frameworks may add sections):

```markdown
# <Project> — Daily report YYYY-MM-DD

Run: <ISO timestamp> · Type: baseline | incremental · Status: complete | partial | failed

## Coverage
Effective sources and, for each, checked / partial / failed and the window covered.

## New items
## First observations
## Material changes
## Repeated observations
## Unverified leads
## Issues and limitations
## State changes
```

Each item lists its ID, title, source link(s), relevant dates, a short evidence summary and its classification. Empty sections say "None". Periodic reports synthesize daily reports only, link each finding to its daily report and original source, and add no unverified claims.

## 9. Failures and validation

- **Source failure** — record it under Coverage, do not advance that source's coverage, continue with other sources. Status: partial.
- **Operation failure** — within a source, continue independent operations after one fails while the budget permits. Report each operation as complete, incomplete (attempted but not fully retrieved) or unattempted (not run, with the reason). Only complete operations count toward coverage or a checkpoint. Candidates from an incomplete operation may be kept as unverified leads; the operation stays incomplete.
- **Budget exhausted** — stop discovery, record what remains uncovered. Status: partial.
- **Fatal error** — write a failed report with the reason; leave `state.json` unchanged except `last_run`; commit and push the report if possible.
- **Before committing** — `state.json` parses and has the core fields; coverage advanced only by the coverage rule; no checkpoint lists an operation that did not complete; every new or changed item in state appears in the report; every finding has a link; the report date is the execution date.
- **Push failure** — report it in the run output and send no email.

## 10. Persistence and email

- Commit message: `research: YYYY-MM-DD <type> <status>`. Push to `main` and confirm success.
- Email only when configured in `PROJECT.md` and a delivery tool is available, and only after a confirmed push. This applies to complete, partial and failed runs alike. Content: the run status, a short summary and the report's repository path or link.
- Never resend automatically. A failed or uncertain delivery is stated in the run's final output as a notification failure, separate from research status. No commit is made solely to record delivery status.
