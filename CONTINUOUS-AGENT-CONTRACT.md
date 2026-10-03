# URF Continuous Research Agent Contract

Execution contract for Continuous research: incremental, coverage-based research relative to previous observations, run on a schedule or manually, with persistent state and bounded per-run work. A run selects it with `Contract: continuous` (common section 1). It follows `RESEARCH-CONTRACT.md` (the common contract); every rule there applies. This file adds only the Continuous rules. A private project holds a read-only copy at `framework/CONTINUOUS-AGENT-CONTRACT.md`.

## 1. Files and outputs

As the further files of common section 1, item 5 (after the project files), each run reads:

1. `state.json`.
2. The most recent daily report; on a synthesis day, every daily report of the period.

`state.json` and the reports needed for the run are always read fresh. The research agent writes only `state.json` and `reports/`.

## 2. Invariants

Not configurable, in addition to common section 3.

- **C1 Coverage** (formerly I4). Never advance a source's coverage beyond the period that is fully checked (section 3).
- **C2 State continuity** (formerly part of I5). Never compact historical identifiers. A failed run leaves the last successful state intact.

## 3. Run type and coverage

Each effective source has an entry in `state.json` `sources` (section 4). When discovery is unrestricted, entries are keyed by the discovery methods named in `FRAMEWORK.md` (for example `web-search`). An entry's `covered_through` is the end of the contiguous period, starting at its `from` date, that has been fully checked: every discovery operation the framework requires for that period completed successfully, in this run or through a valid checkpoint, and every result was screened. Relevant candidates not yet verified remain in `pending_leads`; verifying them is not required for coverage.

Date-bounded discovery ends at the **last complete day**: the day before the execution date, or, when the framework defines a source's day boundaries in another time zone, the last calendar day fully elapsed in that zone when the run starts. The execution date has not fully elapsed during the run, so it is never checked or covered; it becomes eligible in a later run. A source already covered through the last complete day has no search period in that run. Methods the framework defines as recency-based rather than date-bounded follow the framework's rule.

- **Baseline** — `baseline.status` is `not_started` or `in_progress`. At the first baseline run, fix `baseline.window` as absolute dates: `to` is the last complete day and `from` is `to` minus the configured baseline window; every source entry starts at that `from`. Work each source from its coverage toward `window.to` within the budget, prioritizing relevant and significant historical items over exhaustive collection. Set `baseline.status` to `complete` when every source effective at baseline start has `covered_through` on or after `window.to`. An unfinished baseline continues in the next run.
- **Incremental** — baseline complete. Search each source from the day after its `covered_through` through the last complete day, so periods left uncovered by partial or failed runs are revisited before coverage advances. Frameworks may define a small overlap. Re-verify recorded items when new evidence appears or their verification interval is due.
- **Source baseline** — a source newly in the effective Allowed list gets an entry with `from` set to the execution date minus the baseline window, and is worked the same way within the run budget.

Changing sources never erases history: disabled sources stop discovery; newly enabled sources get a source baseline. (Effective sources: common section 4.)

**Coverage rule.** At the end of a run, advance a source's `covered_through` only to the end of the contiguous period, starting at its current coverage, that this run fully checked. A failed source or a failed run advances nothing. A period counts as fully checked only when every operation it requires has completed, in this run or through a valid checkpoint (section 4); a checkpoint itself never advances coverage.

## 4. state.json

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

## 5. Workflow

Steps marked *common* are defined in common section 5.

1. Pull the latest project `main`. Load files as in common section 1 and section 1 above.
2. Record the execution date, available tools and permissions (*common*).
3. Determine the run type and each source's search period (section 3), and compute effective sources (common section 4).
4. Discover candidates within effective sources and budget (*common*).
5. Screen candidates against scope, relevance, `state.json` and the framework's change indicators (*common*).
6. Verify relevant candidates against original sources (*common*).
7. Analyze relevance and extract the framework's target fields (*common*).
8. Compare with previous observations.
9. Classify each item (section 6), using the framework's identity and change rules; handle reappearing historical IDs as in section 4.
10. Write the daily report (section 6) and update `state.json` (section 4).
11. On the configured synthesis day, write the periodic report from the period's daily reports.
12. Validate (common section 7 and section 7 below), commit and push; confirm the push succeeded.
13. If email is configured and a delivery tool is available, send it (common section 8).

## 6. Reports

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

Each item follows common section 6. Periodic reports synthesize daily reports only, link each finding to its daily report and original source, and add no unverified claims.

## 7. Failures and validation

In addition to common section 7:

- **Source failure** — also record it under Coverage and do not advance that source's coverage.
- **Operation failure** — only complete operations count toward coverage or a checkpoint.
- **Budget exhausted** — stop discovery, record what remains uncovered. Status: partial.
- **Fatal error** — also leave `state.json` unchanged except `last_run`.
- **Before committing** — also: `state.json` parses and has the core fields; coverage advanced only by the coverage rule; no checkpoint lists an operation that did not complete; every new or changed item in state appears in the report.

## 8. Persistence

- Commit message: `research: YYYY-MM-DD <type> <status>`.
