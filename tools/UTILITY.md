# URF State Utility

Reference for `framework/tools/urf.py`, used by every Continuous run (`CONTINUOUS-AGENT-CONTRACT.md`). The utility owns `state.json`: it validates every change, selects what the agent needs and publishes atomically. The agent keeps discovery, relevance judgement, evidence verification and reporting, and never loads the whole state file.

Run from the project root: `python3 -I framework/tools/urf.py <command> …`. Inputs are JSON files; each command prints one JSON object. Exit codes: `0` success; `2` validation failure, nothing written; `3` precondition failure, nothing written. Framework parameters come from `framework/state-profile.json`.

## Commands

| Command | Use |
|---|---|
| `begin --now <UTC ISO time> --config <file>` | Start or resume the run; prints the plan. |
| `record --file <file>` | Record one discovery operation; returns the classification of its candidates. |
| `apply --file <file>` | Apply a batch of change operations, all or nothing. |
| `queue --n <N>` | Leads to verify now, and items due for re-verification. |
| `show --id <ID> [--id …]` | Records of specific entries. |
| `summary` | Counts, derived status and Markdown for the Coverage, State changes and Unverified leads sections, and the generated run accounting. |
| `finish --status complete\|partial\|failed --report <file> [--fatal <reason>]` | Validate and publish `state.json` and the report. |
| `validate [--published]` | Check invariants without writing. |
| `discard` | Maintainer only: move unusable staging to `.urf/preserved/`. |
| `apply --repair --file <file>` | Maintainer only: approved repairs on published state, outside a run. |

### begin

Config file:

```json
{ "contract": "continuous", "push_available": true, "baseline_window_days": 60,
  "budgets": { "search": 20, "verify": 60, "reverify": 10 },
  "baseline_budgets": { "search": 40, "verify": 40 },
  "reverify_interval_days": 30,
  "methods": { "github.com/search-new": { "config": "depth=30 forks=exclude", "operations": ["topic:x", "topic:y"] } } }
```

`push_available` states truthfully whether the run can push (`true` or `false`). `publication_mode` is `automatic` (the default: push access required) or `manual-supervised`, which also needs `maintainer_authorization`, the maintainer's explicit authorization text naming the run's execution date (`YYYY-MM-DD`). It is for supervised runs only, never unattended ones (`RESEARCH-CONTRACT.md` section 5): `finish` then requires the report to state that publication is pending maintainer push, and its output lists the files as `written_locally` with `remote_publication` pending, not as published. Send no email.

`budget_override` (optional) raises or lowers named budgets for this run only: `{ "budgets": { "search": 40 }, "authorization": "<maintainer's text naming the execution date>" }`. `begin` refuses it (exit 3) without an authorization naming the run's execution date, or when it names an unknown budget or a value that is not a non-negative integer. The manifest records the base and overridden budgets and the authorization; the next run uses its own configuration again. The override stays a hard limit.

Take budgets, window and methods from `PROJECT.md` and the framework defaults (project overrides win); `baseline_budgets` applies only to baseline runs; omit `reverify_interval_days` to use the framework value. `methods` lists the enabled discovery methods with their shared config string and operations (the exact query text, or `owner/repo` for a list).

`--now` is the run start time; its UTC date is the execution date and the last complete day is the day before. The plan gives the run type, the baseline window, each method's search periods (baseline sub-periods oldest first), operations reusable from a valid checkpoint, budgets, counts and warnings.

`begin` stops (exit 3) without changing anything when: push access is unavailable in `automatic` mode, `push_available` is not a boolean, `publication_mode` is unsupported, or `manual-supervised` lacks an authorization naming the execution date; `state.json` cannot be parsed or fails validation; `state.json` or `reports/` have uncommitted changes; published files from `finish` are not yet committed (it names them); or staging exists that cannot be resumed (another UTC date, changed published state, changed configuration). Same-date staging with unchanged state and configuration is resumed. After a committed publication, staging is cleaned up (a failed run's staging is moved to `.urf/preserved/`).

### record

```json
{ "method": "github.com/search-new", "period": "2026-10-09..2026-10-09", "op": "topic:x",
  "status": "complete", "requests": 1,
  "incomplete_results": false, "fields_complete": true, "pages_read": 1, "pages_required": 1,
  "total_count": 75, "items_read": 30, "depth": 30,
  "candidates": [ { "name": "owner/repo", "repo_id": 123, "archived": false } ] }
```

`status` is `complete`, `incomplete` or `unattempted`. The fields after `requests` are those the profile's completion checks name for the method; a `complete` status that fails a check is recorded as `incomplete` with the reasons. `requests` counts against the search budget. To reuse an operation from the plan's `reusable` list: `{"method": …, "period": …, "op": …, "reuse": true}`, adding `"confirmed": true` when the plan marks it `needs_confirmation` (a legacy report: confirm it records the operation as complete).

The classification counts and the IDs of new candidates are kept with the operation record in staging; the run accounting is generated from them. Returns counts per class (`new`, `item`, `historical`, `rejected`, `pending`, `dup_in_run`) and, in full, only: `new` candidates; recorded items whose visible indicators or name changed (`changed_items`); historical entries seen again; pending leads that gained an identifier or name (`enrich`).

### apply

A JSON list of operations. The batch is checked against every invariant before anything is written.

| Operation | Fields | Effect |
|---|---|---|
| `lead.add` | `name`, secondary key, `category`, `method`, `period`, optional `extra` | New pending lead, first seen on the execution date; refused if the ID or secondary key is already known. |
| `lead.enrich` | `id`, `set` (secondary key and/or `name`) | Keeps first-seen date, method and period. |
| `lead.accept` | `id`, `item` (framework fields, allowed relevance) | Item added; counts one verification. |
| `lead.reject` | `id`, `relevance` (a rejection label), `reason` | Moved to `rejected_ids`; counts one verification. |
| `lead.fail` | `id`, `reason` | Temporary failure: stays pending, not retried this run; counts one verification. |
| `lead.resolve` | `id`, `matched`, `reason` | Removes a lead that duplicates a recorded entry. |
| `lead.drop` | `id`, `reason` | Removes a lead; the reason goes in the report. |
| `screen.drop` | `name` or `id`, `reason` | Screening drop, for the report only. |
| `item.observe` | `id` | Repeated observation (`last_seen`). |
| `item.verify` | `id`, `set`, `fingerprint`, `material`, `changes` | Re-verification; counts one re-verification. |
| `item.rename` | `id`, `new_name` | Old name added to `aliases`; the ID never changes. |
| `item.deactivate` | `id`, `reason` | Moved to `historical_ids` with its identity fields. |
| `item.reactivate` | `id`, `item` | Back to `items` on verified evidence. |

Results for accepted and rejected leads include the lead's `discovery_period`, used to classify New versus First observation. Repairs (`--repair`, no run in progress, each with a `reason`): `source.set_coverage`, `baseline.set_window`, `item.add_alias`, `lead.resolve`.

### queue, show, summary

`queue --n N` returns at most `N` leads, limited by the remaining verification budget: the reserve (the profile's fraction of `N`, rounded up, oldest first) and then the normal order; leads already attempted in the run are excluded. The slot (`reserve` or `normal`) of every lead it returns is kept in staging (the first assignment wins); verification outcomes record it with the lead's category and first-seen date. It also lists items due for re-verification, oldest `last_verified` first, limited by the remaining re-verification budget, with the total due.

`summary` returns the coverage each method would reach, the derived run status, counters, the IDs the report must list, and Markdown: a coverage table with every operation's status, the state changes, and the Unverified leads section (leads added this run, temporary failures this run, and backlog counts by category and first-seen date). `markdown.accounting` is the run accounting the report must carry unchanged: budgets used and any override, search requests by operation kind, a per-operation table (total, read, requests, candidates, new leads added, dropped and not handled, already pending, recorded items, historical, previously rejected, duplicates in the run, not already recorded) and verification outcomes by slot and by category. It is generated only from the persisted records of `record`, `queue` and `apply`, between `<!-- urf-accounting:begin -->` and `<!-- urf-accounting:end -->`.

### finish

Checks that the requested status matches the operation outcomes (`failed` for partial outcomes needs `--fatal <reason>`); that the report states the execution date, `Status: <status>`, any fatal reason and every ID acted on in the run; and every invariant. It regenerates the run accounting: a report that carries the block must carry it unchanged (otherwise the report is rejected; run `summary` again after the last change); a report without it gets it appended. It appends a machine-readable `urf-ops` block to the report, then writes the report (`reports/daily/<date>.md`, or the next free suffix) and `state.json`, and prints the commit command. A failed run publishes the report and `last_run` only. Commit both files together. If publication was interrupted, run `finish` again.

## Invariants

IDs follow the profile pattern and are unique across items, historical entries, rejected entries and pending leads, by ID and by secondary key; historical entries keep their identity fields; items are `active`; no item, historical entry or rejected entry disappears, and no lead disappears without an operation; the baseline window never changes once fixed; coverage only advances, only over contiguous periods whose every configured operation completed (or was reused from a valid checkpoint), and never beyond the last complete day (the execution date for recency-based methods); checkpoints name only completed operations; budgets are respected; only declared top-level keys exist.

## Known limitation

Inputs added after coverage (audit L-4) are not detected: a new query or list is run only from the method's current coverage onward. See `CONTINUOUS-AGENT-CONTRACT.md` section 3.
