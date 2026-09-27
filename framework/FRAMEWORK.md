# Repo Scout Framework

Specializes `RESEARCH-CONTRACT.md` for public source-code repositories, primarily on GitHub, in any technical domain. Each project supplies its subject, discovery inputs and relevance criteria. Nothing here weakens the contract's invariants (section 3).

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
| Repository search (`github.com/search`) | For each query, two passes sorted by stars: **new** `<query> created:P`, and **established** `<query> pushed:P stars:>=<threshold>`. Read each pass to the search depth. | Every required query and pass ran for P, and every result page within the configured depth (or to the total, if smaller) was retrieved completely, with the required fields, and screened. A total above the depth completes the procedure but is a bounded search: the report records the total, the depth examined and that results beyond the depth were not examined. Any failed, incomplete, summarized or truncated retrieval leaves P unchecked. |
| Curated lists (`github.com/lists`) | For each configured list repository, read the changes to its list files over P from Git history. | Every configured list's changes over P were read and every added repository link screened. |
| Web search (`web-search`) | Run each web query with results restricted to effective Allowed domains; screen the top results to the web depth. | Search engines do not bound dates reliably, so this method is checked only for the run date: every query ran and its top results were screened. Coverage advances to the run date and the report labels the method recency-based. |

The baseline window is worked in calendar-month sub-periods, oldest first, so coverage advances contiguously and an interrupted baseline resumes at the next unchecked month. An incremental run treats its whole search period as one sub-period. Coverage means the configured procedure was completed for the period; it never means every matching repository on the host was found. Star-sorted passes prioritize discovery; they do not monitor recorded repositories for changes.

## Screening
Using search and list metadata only, before verification:
- Map forks, mirrors and renamed repositories to their IDs.
- Skip recorded items whose visible indicators (pushed date, archived flag, default branch) show no possible material change and whose re-verification is not due; count them as repeated observations.
- Drop placeholders and candidates clearly outside the project's scope.
- Rank the rest by likely relevance; candidates beyond the verification budget become pending leads, retried first in the next run.

## Verification
- The original source is the repository itself. Verify existence, canonical name, `repo_id`, purpose (description and README), license, archived status, creation date, latest release and latest tag.
- Required fields for a verified finding: `repo_id` or canonical name, creation date, archived flag, license (or its verified absence), latest release or tag with its date (or verified none). Dates and versions come from structured data: host API fields (`created_at`, `pushed_at`, `published_at`, `license.spdx_id`, `archived`) or Git data (tag and commit dates). Quote the raw value. Never take a date or version from a summarized page or infer a missing one; if a required field is unavailable, report the item as an unverified lead.
- Attribute capability and performance claims to their source ("the README states …"); do not assert them.
- Evidence tiers, stated per finding: **A** primary artifact (repository metadata, release, tag, commit, license file); **B** credible secondary source that links to the repository (maintainer announcement, documentation site); **C** community signal or unverified lead. Stars, forks and trending are discovery signals, not evidence of quality.

## Relevance
Label each verified candidate **high**, **medium** or **low** against the project's relevance criteria, with a one-line reason. Consider scope match, substance (working code or documentation beyond a placeholder), maintenance (recent commits, releases, issue activity), a present and usable license, and adoption signals. High and medium items are reported as findings; low items are counted in Coverage only.

## Change indicators and material changes
`fingerprint`: latest release tag, latest tag, archived flag, license SPDX ID, canonical name, default branch.

Material: a new release or tag that changes the MAJOR or MINOR version (any new release for repositories without semantic versioning); archived or unarchived; license change; rename or transfer; deleted or made private; deprecation or a successor declared in the README.

Not material: star and fork counts, routine commits, patch releases, description or topic edits. These may update item fields without being reported as changes.

## Inactive items
Move an item to `historical_ids` when one is verified: it is archived; it is deleted or private (not found through both Git and the host); or its default branch has had no commits for 12 months (projects may override). A reappearing item is active again only when verified unarchived, public again or showing new default-branch commits; classify it by comparing with its stored fingerprint.

## Re-verification interval
Active items: every 30 days, whether or not they appear in current search results; each run re-verifies due items from `state.json` within the re-verification budget, and due items beyond it are reported and carried to the next run. Screening metadata showing a changed indicator triggers re-verification earlier.

## Additional state fields
Item fields: `name` (current `owner/repo`), `repo_id`, `created`, `latest_release`, `license`, `relevance`, `aliases` (optional). Source-native checkpoints: not used.

## Report additions
Per finding: repository link; type; one-line purpose; created date; latest release or tag with date; license; activity (last commit month, release cadence if evident); documented requirements and self-hosting notes; security caveats found; evidence tier; relevance label and reason. Material changes show old → new values with evidence.

Coverage, per method and sub-period: queries run, results available and read, and for bounded searches the total, the depth examined and the limitation, candidates screened, verified, duplicates, failures and the access path used.

Weekly synthesis: a deduplicated shortlist of the period's high-relevance findings and material changes; candidate experiments only if the project requests them.

## Defaults
- Baseline window: 180 days.
- Baseline budget: up to 3 runs; per run at most 40 search requests and 40 verifications.
- Per-run budget: at most 20 search requests, 20 verifications and 10 re-verifications.
- Search depth: 30 results per query pass. Web depth: 10 results per query.
- Established-pass star threshold: 500.
- Weekly synthesis day: Friday.

## Departures from contract defaults
- Coverage entries are keyed by discovery method (`github.com/search`, `github.com/lists`, `web-search`) even though the Allowed list is restricted, because one source hosts several independent methods. Each entry follows the contract's coverage rule.
- Verification links are permitted (`framework/SOURCES.md`).
