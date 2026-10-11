# URF Continuous Research Agent Contract

Execution contract for Continuous research: incremental, coverage-based research relative to previous observations, run on a schedule or manually, with persistent state and bounded per-run work. A run selects it with `Contract: continuous` (common section 1). It follows `RESEARCH-CONTRACT.md` (the common contract); every rule there applies. This file adds only the Continuous rules. A private project holds a read-only copy at `framework/CONTINUOUS-AGENT-CONTRACT.md`.

## 1. Files and outputs

As the further files of common section 1, item 5 (after the project files), each run reads:

1. `framework/tools/UTILITY.md`, the reference for the state utility `framework/tools/urf.py`.
2. On a synthesis day, every daily report of the period.

The agent reads and changes `state.json` only through the state utility, which returns the plan, the classification of candidates, the verification queue and the records the run needs; the agent never loads the whole file. The utility validates every change and publishes `state.json` atomically. Progress of an unfinished run is kept in the local staging directory `.urf/run/`, which is never committed. The research agent writes only `state.json` (through the utility) and `reports/`.

## 2. Invariants

Not configurable, in addition to common section 3.

- **C1 Coverage** (formerly I4). Never advance a source's coverage beyond the period that is fully checked (section 3).
- **C2 State continuity** (formerly part of I5). Never compact historical identifiers. A failed run leaves the last successful state intact.

## 3. Run type and coverage

Each effective source has an entry in `state.json` `sources` (section 4). Entries are keyed by source, or by discovery method where the framework so defines (for example `web-search`). An entry's `covered_through` is the end of the contiguous period, starting at its `from` date, that has been fully checked: every discovery operation the framework requires for that period completed successfully, in this run or through a valid checkpoint, and every result was screened. Relevant candidates not yet verified remain in `pending_leads`; verifying them is not required for coverage.

The **execution date** of a Continuous run is the UTC calendar date at run start. It names the run's report and is the date recorded in state (`last_run.date`, `first_seen`, `last_seen`, `last_verified`, `inactive_since`). Date-bounded discovery ends at the **last complete day**, the day before the execution date. The execution date has not fully elapsed during the run, so it is never checked or covered; it becomes eligible in a later run. A source already covered through the last complete day has no search period in that run.

A **recency-based** method, one the framework declares cannot bound results by date, is fully checked for the execution date when every configured operation completed and its results were screened. Its `covered_through` becomes the execution date, its first complete pass completes its baseline, and each later run repeats the pass.

Relevance decides which candidates become pending leads or items and which leads are verified. It never stops a discovery operation early and never limits coverage.

- **Baseline** — `baseline.status` is `not_started` or `in_progress`. At the first baseline run, fix `baseline.window` as absolute dates: `to` is the last complete day and `from` is `to` minus the configured baseline window; every source entry starts at that `from`. Work each source from its coverage toward `window.to` within the budget. Set `baseline.status` to `complete` when every source effective at baseline start has `covered_through` on or after `window.to`. An unfinished baseline continues in the next run.
- **Incremental** — baseline complete. Search each source from the day after its `covered_through` through the last complete day, so periods left uncovered by partial or failed runs are revisited before coverage advances. Frameworks may define a small overlap. Re-verify recorded items when new evidence appears or their verification interval is due.
- **Source baseline** — a source newly in the effective Allowed list gets an entry with `from` set to the last complete day minus the baseline window, and is worked the same way within the run budget.

Changing sources never erases history: disabled sources stop discovery; newly enabled sources get a source baseline. (Effective sources: common section 4.)

**Open issue — inputs added after coverage (audit L-4, unresolved).** Coverage records that the operations configured when a period was checked completed. A discovery input (for example a query or curated list) added later has not been run over periods already covered, and nothing yet records or discloses that. Until this is resolved, a source's coverage must not be taken as historical coverage for inputs added after its periods were checked.

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

Frameworks declare their additional fields, including any top-level fields, in their state profile (`framework/state-profile.json`). Additive fields do not change `schema_version`.

- `items` — active items keyed by the framework's stable ID: `first_seen`, `last_seen`, `last_verified`, `status` (always `active`), `fingerprint` (the framework's change indicators), `report` (path of the report that last described the item), plus framework-defined fields.
- `baseline.window` — absolute `from` and `to` dates, fixed at the first baseline run.
- `sources` — one entry per effective source or discovery method: `from`, `covered_through`, `last_status`, and optionally `checkpoint`. Entries of disabled sources are kept.
  - `last_status` — result of the most recent run that worked the source: `complete` (every required operation for the periods worked completed), `partial` (some completed; others incomplete or unattempted) or `failed` (none completed). A source not worked in a run keeps its value.
  - `checkpoint` — optional, defined by the framework: compact progress within the first period not yet covered (for example completed operations, a cursor or a last ID). It never advances `covered_through`. A later run reuses it only under the framework's validity conditions and otherwise repeats the work. Remove it when that period becomes covered or the checkpoint is invalid.
- `historical_ids` — inactive items keyed by ID, each with `inactive_since`, `fingerprint`, `report` and the framework's identity fields (for example a host's numeric ID, the name and aliases), so a renamed or reappearing item is still recognised. Never removed.
- **Inactive items.** An item moves from `items` to `historical_ids` when the framework's inactivity criterion is verified; if the framework defines none, items stay active. Report the move under State changes.
- **Reappearance.** When a candidate's ID is in `historical_ids`, verify it and compare its evidence and fingerprint with the stored record, and with its report if needed. Classify it by the framework's criteria as a repeated observation or a material change. Move it back to `items` only when verified evidence shows it active again by the framework's criteria.
- `pending_leads` — unverified candidates to retry, each with the date first seen and the framework's lead fields. A lead may come from a period that is not yet covered (a partial run), provided that period lies within the baseline window or the run's search period. Match candidates to existing leads by stable identifier first, then by name; when an identifier becomes available for a name-only lead, add it to that lead and keep its first-seen date and origin. Leads stay until verified, resolved as a duplicate of a recorded entry, or dropped with a reason stated in the report; they are never dropped to reduce size or context.

## 5. Workflow

Steps marked *common* are defined in common section 5.

1. Pull the latest project `main`. Load files as in common section 1 and section 1 above.
2. Record the execution date, available tools and permissions (*common*). Run `begin`: it checks for an unfinished run or publication (section 7), then returns the run type, each source's search period (section 3) and reusable checkpoint operations. Compute effective sources (common section 4).
3. Discover candidates within effective sources and budget (*common*). Record each operation with `record`, which applies the framework's completion checks and classifies its candidates against state.
4. Screen the candidates `record` returns as new or changed against scope and relevance (*common*); add leads and screening drops with `apply`.
5. Take the leads to verify, and the items due for re-verification, from `queue`. Verify them against original sources (*common*); analyze relevance and extract the framework's target fields (*common*).
6. Compare with previous observations and classify each item (section 6), using the framework's identity and change rules; handle reappearing historical IDs as in section 4. Record every outcome with `apply`.
7. Write the daily report (section 6), using `summary` for the Coverage, State changes and Unverified leads sections, and its generated run accounting (per-operation counts and verification by slot and category), unchanged. The agent never reconstructs these counts; `finish` appends the accounting if it is missing and rejects an edited copy.
8. On the configured synthesis day, write the periodic report from the period's daily reports.
9. Run `finish`, which validates (common section 7 and section 7 below) and publishes `state.json` and the report together. Commit both in one commit and push; confirm the push succeeded.
10. If email is configured and a delivery tool is available, send it (common section 8).

## 6. Reports

- Daily: `reports/daily/YYYY-MM-DD.md`, named by the execution date. A further run on the same date uses the next free numeric suffix (`-2`, `-3`, …). Reports named before the UTC rule keep their names.
- Periodic: `reports/periodic/YYYY-Www.md`, named by the ISO week of the synthesis day and produced within the daily run on that day. The period is the seven days ending on the synthesis day, including that day's report. If a later run finds the latest period's synthesis missing, it produces it then.

Classifications:

- **New** — not previously recorded; published within the period in which this project discovered it (this run's search period, or the origin period of the pending lead).
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

Items verified, added, changed, dropped or attempted in this run are listed individually and each follows common section 6. Repeated observations screened without verification, and leads carried over unchanged from earlier runs, are reported as counts (per method, and per category and first-seen date for leads); every pending lead remains in `state.json`. Periodic reports synthesize daily reports only, link each finding to its daily report and original source, and add no unverified claims.

A budget above the configured value applies only under a one-time maintainer authorization naming the execution date (`budget_override`, `UTILITY.md`); the report states it.

## 7. Failures and validation

In addition to common section 7:

- **Source failure** — also record it under Coverage and do not advance that source's coverage.
- **Operation failure** — only complete operations count toward coverage or a checkpoint.
- **Budget exhausted** — stop discovery, record what remains uncovered. Status: partial.
- **Fatal error** — also leave `state.json` unchanged except `last_run`. If `state.json` cannot be parsed, leave it untouched and persist no report; the error appears only in the run output.
- **Interrupted run** — a run that stops before `finish` publishes nothing; it is not a failed run. Its staging is resumed by `begin` on the same execution date when the published state and configuration are unchanged. Otherwise `begin` stops without touching the staging and states the reason; the maintainer inspects it or runs `discard`, which moves it to `.urf/preserved/`. Runs are never resumed on a later date.
- **Unfinished publication** — when `finish` published files that are not yet committed, `begin` stops and names them; commit them before the next run. A publication interrupted between files is completed by running `finish` again.
- **Before committing** — `finish` checks the invariants and the state profile: identity is unique across items, historical entries, rejected entries and pending leads; no item, historical entry or rejected entry disappears; no lead disappears without an operation; coverage advanced only by the coverage rule and never beyond the last complete day; no checkpoint lists an operation that did not complete; budgets were respected; the report states the execution date and status, and lists every entry acted on in the run.

## 8. Persistence

- Commit `state.json` and the report together, after `finish`. The state utility never commits.
- Commit message: `research: YYYY-MM-DD <type> <status>`.
