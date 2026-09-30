# Repo Scout Framework

Specializes the URF contracts — `RESEARCH-CONTRACT.md` and the execution contracts — for public source-code repositories, primarily on GitHub, in any technical domain. Each project supplies its subject, discovery inputs and relevance criteria. Nothing here weakens their invariants (common contract section 3 and each execution contract's section 2).

**Execution contracts.** Repo Scout's domain rules — target, item identity, relevance, verification and evidence, per-finding report fields, and the source guides with effective-source behavior — apply under both `Contract: continuous` and `Contract: deep`, where relevant. Its Continuous operational rules — coverage, state and checkpoints, the pending, rejected and historical lifecycle and re-verification, baseline and incremental runs, and the Continuous budgets and bounded-discovery defaults — apply only under `Contract: continuous`. Configured discovery inputs (queries, curated lists) define a Continuous run's discovery operations and coverage obligations; a Deep run may use relevant ones as starting inputs without being obliged to run them, and may formulate further searches and follow promising paths within the effective sources and the framework and project rules.

Research is read-only: never install, build or execute repository code, use credentials, or open issues or pull requests. Git clones used for metadata live in a scratch location outside the project repository and are discarded after the run.

## Target
An item is one public Git repository: a library, framework, tool, application, reference implementation, model or dataset repository with code or documentation, or a curated list, within the project's scope.

Out of scope unless the project opts in: forks without material divergence, mirrors (mapped to their upstream), empty or placeholder repositories, personal coursework, and repositories that only link elsewhere.

## Item identity
- **ID:** `<host>/<owner>/<repo>` in lower case, for example `github.com/owner/repo`. Record the host's numeric repository ID as `repo_id` when available.
- **Renames and transfers:** the ID never changes. When a recorded repository redirects, or its `repo_id` appears under a new name, update `name`, add the old name to `aliases` and report a material change.
- **Forks:** separate items only if the project opts in and the fork shows material divergence (its own releases or substantial independent development). Otherwise a fork maps to its parent.
- **Mirrors:** a repository declared a mirror in its description or README maps to the upstream ID; record the mirror URL in `aliases`.
- **Monorepos:** the repository is the item. Notable sub-projects are described in the finding, not tracked separately.

## Discovery
Projects define discovery inputs in `PROJECT.md` under `## Discovery inputs`: search queries, the established-pass star threshold, curated list repositories, web queries and the fork policy. A method without inputs is disabled. Procedures are in `framework/sources/github.md`.

| Method (coverage key) | Procedure | Fully checked for a period P when |
|---|---|---|
| New repositories (`github.com/search-new`) | For each query, `<query> created:P`, sorted by stars, read to the search depth. | Every query completed for P, in this run or through a valid checkpoint: every result page within the configured depth (or to the total, if smaller) was retrieved completely, with the required fields, and screened. A total above the depth completes the procedure but is a bounded search: the report records the total, the depth examined and that results beyond the depth were not examined. Any failed, incomplete, summarized or truncated retrieval leaves P unchecked. |
| Established repositories (`github.com/search-established`) | For each query, `<query> pushed:>=<P start> stars:>=<threshold>`, sorted by stars, read to the search depth. | As for new repositories, for every query. |
| Curated lists (`github.com/lists`) | For each configured list repository, read the changes to its list files over P from Git history. | Every configured list's changes over P were read, in this run or through a valid checkpoint, and every repository added to its list files during P screened. A repository is added when a commit in P on the first-parent history of the list repository's default branch links a repository ID (see Item identity) that the list files did not link immediately before that commit; moving, reformatting, sorting or editing a line without introducing a new repository ID is not an addition, and a repository added and later removed within P is still an addition. |
| Web search (`web-search`) | Run each web query with results restricted to effective Allowed domains; screen the top results to the web depth. | Search engines do not bound dates reliably, so this method is checked only for the run date: every query ran and its top results were screened. Coverage advances to the run date and the report labels the method recency-based. |

The baseline window is worked in calendar-month sub-periods, oldest first, for new repositories and curated lists, so coverage advances contiguously and an interrupted baseline resumes at the next unchecked month. Established-repository discovery runs once across the whole baseline window (P = the fixed window), and its coverage is tracked separately; the baseline is complete only when all three methods reach the window end. An incremental run treats its whole search period as one sub-period for every method, so established discovery recurs in every run for the period since its coverage.

Each query pass and each list read is one operation. Run every configured operation for the period; after an individual failure, continue with the remaining operations while the budget permits, and record each as complete, incomplete or unattempted (common contract section 7; Continuous contract section 7).

**Checkpoint.** When a run leaves a method's current period incomplete, store progress in that method's `sources` entry (the entry key names the method):

```json
"checkpoint": { "period": "2026-05-01..2026-05-31", "config": "depth=20 forks=exclude", "done": ["topic:llm-inference", "topic:rag"], "report": "reports/daily/2026-05-02.md" }
```

- `done`: operations completed for `period`, each identified by its own text — the exact query string for a search, `owner/repo` for a curated list. Only complete operations are listed.
- `config`: the shared parameters that apply to every operation of the method — search depth and fork policy; also the star threshold for established discovery; the list files read for curated lists. Query text is not part of `config`.
- `report`: the committed report holding evidence for every operation in `done`: each is recorded there as complete (total, items read, candidates) or as reused with a link to the report where it completed. Relevant candidates from those operations are already in `pending_leads`, `items` or `historical_ids`.
- **Shared changes.** A different `period`, a change to any shared parameter in `config`, or a missing `report` invalidates the whole checkpoint: run every operation.
- **Query changes.** With the period and shared parameters unchanged, a query change affects only that query: an edited or added query runs, and a removed query is dropped from `done`. The other completed operations stay reusable.
- **Reuse.** Skip an operation in `done` only when `report` records it as complete, or as reused with a link to a report that exists and records it as complete. Otherwise run it.
- **Repeated interruptions.** When a run reuses operations and the period is still incomplete, that run's report becomes the checkpoint's `report`, and `done` keeps both the reused and the newly completed operations. The report links each reused operation to the report where it completed — the original evidence, never an intermediate report — so every operation's evidence stays one link away however many runs are interrupted.
- When the period becomes covered, remove the checkpoint. In incremental runs the period end moves with each run, so an earlier checkpoint normally does not match and the period is searched again.

GitHub's `pushed:` qualifier matches a repository's latest push date. `pushed:>=<P start>` therefore finds repositories with any push on or after P's start, that is, repositories active since then. It cannot reconstruct activity within an individual past month, so established discovery is never run per historical month. Coverage means the configured procedure was completed for the period; it never means every matching repository on the host was found. Star-sorted passes prioritize discovery; they do not monitor recorded repositories for changes. Established discovery is bounded and star-sorted: it reads only the highest-starred active repositories to the search depth. In daily runs these are mostly already recorded, so relevant repositories ranked beyond the depth are not examined; the report's count of established results not already recorded shows how much new discovery each run actually yields.

## Screening
Using search and list metadata only, before verification:
- Map forks, mirrors and renamed repositories to their IDs.
- Match candidates to pending leads by `repo_id`, then by name (case-insensitive). Add a missing `repo_id` to a name-only lead, and update `name` when a lead's `repo_id` appears under a new name; keep the lead's `first_seen`, method and period.
- Skip candidates in `rejected_ids` and count them as previously rejected. A candidate matches an entry by `repo_id` when both are known, otherwise by ID (see Item identity).
- Skip recorded items whose visible indicators (archived flag, default branch) show no possible material change and whose re-verification is not due; count them as repeated observations. Full metadata, including `pushed_at`, is retrieved only when verifying.
- Drop placeholders and candidates clearly outside the project's scope.
- Add the rest to `pending_leads`; verification follows *Pending leads* below.

## Pending leads
Verify pending leads in this order: category (project Scope order), then oldest `first_seen`, then repository name compared case-insensitively. Reserve the first quarter of the run's verification budget, rounded up, for the oldest leads regardless of category (oldest `first_seen`, then category, then name); the rest follows the normal order.

Outcomes:
- **High or medium relevance:** remove from `pending_leads` and add to `items`.
- **Low relevance, or confirmed out of scope:** remove from `pending_leads` and add to `rejected_ids`; the report states the reason.
- **Temporary failure** (a request failed, timed out, was rate-limited or returned incomplete data): the attempt counts against the verification budget; the lead stays pending and is not attempted again in this run.

## Verification
- The original source is the repository itself. Verify existence, canonical name, `repo_id`, purpose (description and README), license, archived status, creation date, latest release and latest tag.
- Required fields for a verified finding: `repo_id` or canonical name, creation date, archived flag, license (or its verified absence), latest release or tag with its date (or verified none). Dates and versions come from structured data: host API fields (`created_at`, `pushed_at`, `published_at`, `license.spdx_id`, `archived`) or Git data (tag and commit dates). Quote the raw value. Never take a date or version from a summarized page or infer a missing one; if a required field is unavailable, report the item as an unverified lead.
- Attribute capability and performance claims to their source ("the README states …"); do not assert them.
- Evidence tiers, stated per finding: **A** primary artifact (repository metadata, release, tag, commit, license file); **B** credible secondary source that links to the repository (maintainer announcement, documentation site); **C** community signal or unverified lead. Stars, forks and trending are discovery signals, not evidence of quality.

## Relevance
Label each verified candidate **high**, **medium** or **low** against the project's relevance criteria, with a one-line reason. Consider scope match, substance (working code or documentation beyond a placeholder), maintenance (recent commits, releases, issue activity), a present and usable license, and adoption signals. High and medium items are reported as findings; low items are not findings, and in Continuous runs they are counted in Coverage only.

## Change indicators and material changes
`fingerprint`: latest release tag, latest tag, archived flag, license SPDX ID, canonical name, default branch.

Material: a new release or tag that changes the MAJOR or MINOR version (any new release for repositories without semantic versioning); archived or unarchived; license change; rename or transfer; deleted or made private; deprecation or a successor declared in the README.

Not material: star and fork counts, routine commits, patch releases, description or topic edits. These may update item fields without being reported as changes.

## Inactive items
Move an item to `historical_ids` when one is verified: it is archived; it is deleted or private (not found through both Git and the host); or its default branch has had no commits for 12 months (projects may override). A reappearing item is active again only when verified unarchived, public again or showing new default-branch commits; classify it by comparing with its stored fingerprint.

## Re-verification interval
Active items: every 30 days, whether or not they appear in current search results; each run re-verifies due items from `state.json` within the re-verification budget, and due items beyond it are reported and carried to the next run. Screening metadata showing a changed indicator triggers re-verification earlier.

## Additional state fields
Item fields: `name` (current `owner/repo`), `repo_id`, `created`, `latest_release`, `license`, `relevance`, `aliases` (optional). Source checkpoint: `checkpoint` (see Discovery).

Top-level `rejected_ids` (optional): repositories rejected after verification. Each key is the repository's ID (see Item identity), used for name matching; each value is its `repo_id`, or `null` when unknown. Created on the first rejection; entries are kept.

```json
"rejected_ids": { "github.com/owner/repo": 123456789 }
```

## Report additions
Per finding: repository link; type; one-line purpose; created date; latest release or tag with date; license; activity (last commit month, release cadence if evident); documented requirements and self-hosting notes; security caveats found; evidence tier; relevance label and reason. Material changes show old → new values with evidence.

Coverage, per method and sub-period: each operation's status (complete, incomplete, unattempted, or reused from a checkpoint with a link to the report where it completed), queries run, results available and read, for established discovery how many results read were not already recorded, and for bounded searches the total, the depth examined and the limitation, candidates screened, verified, duplicates, failures and the access path used.

Weekly synthesis: a deduplicated shortlist of the period's high-relevance findings and material changes; candidate experiments only if the project requests them.

## Defaults
- Continuous baseline window: 180 days.
- Continuous baseline budget: up to 3 runs; per run at most 40 search requests and 40 verifications.
- Continuous per-run budget: at most 20 search requests, 20 verifications and 10 re-verifications.
- Continuous search depth: 30 results per query pass. Continuous web depth: 10 results per query.
- Established-pass star threshold: 500.
- Weekly synthesis day: Friday.

## Departures from contract defaults
- Coverage entries are keyed by discovery method (`github.com/search-new`, `github.com/search-established`, `github.com/lists`, `web-search`) even though the Allowed list is restricted, because one source hosts several independent methods. Each entry follows the coverage rule of the Continuous contract (section 3).
- Verification links are permitted (`framework/SOURCES.md`).
