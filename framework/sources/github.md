# GitHub Source Guide

## Access paths
Confirm at the start of each run which paths work and record them in the report: under Coverage in Continuous runs, under Method in Deep runs. Use whichever tool is available; the framework does not depend on a specific integration.

1. **GitHub MCP server (preferred when available)** — read-only tools only:
   - `search_repositories` — discovery with compact output (`minimal_output: true`); single-repository metadata with the query `repo:{owner}/{repo}` and full output (`minimal_output: false`).
   - `list_releases` with `fields: tag_name, published_at, prerelease, draft` — release dates. Avoid tools that return full release bodies.
   - `list_tags` and `get_commit` (`detail: none`) — tag names and the dates of tagged commits.
   - `get_file_contents` — README, license and list files.
2. **REST API (JSON)** — the same endpoints directly: `GET /search/repositories?q=<query>&sort=stars&order=desc&per_page=<depth>&page=<n>`, `GET /repos/{owner}/{repo}`, `GET /repos/{owner}/{repo}/releases`. Unauthenticated search allows only a few requests per minute.
3. **Git protocol** — `git ls-remote --tags https://github.com/{owner}/{repo}.git`; a metadata-only clone in scratch, `git clone --bare --filter=blob:none https://github.com/{owner}/{repo}.git`, for curated-list history and precise tag and commit dates.
4. **Web pages** — README and documentation text, for purpose and requirements only.

Pace requests to the path's rate limit. In Continuous runs, count each discovery search request, including each page, against the search budget. Requests made to verify or re-verify a repository, including `repo:` searches, count only toward that repository's verification or re-verification.

If no path returns structured dates, verification is incomplete: report affected candidates as unverified leads. Tools that summarize pages can misstate dates and versions; take them only from raw API fields or Git output.

## Repository search
- Date qualifiers use whole days. New repositories: `created:YYYY-MM-DD..YYYY-MM-DD`. Established repositories: `pushed:>=YYYY-MM-DD` with `stars:>=<threshold>`.
- `pushed:` filters on a repository's latest push date, not on pushes within a range: `pushed:2026-04-01..2026-04-30` returns only repositories whose last push fell in April. Never use a closed `pushed:` range for discovery.
- Use compact results for discovery. Required fields per item: `full_name`, `id`, `created_at`, `fork` and `archived`. `pushed_at` is not required in discovery results: the `pushed:>=` qualifier already bounds activity, and `pushed_at` is retrieved at verification.
- A result list is complete when `incomplete_results` is false, every page within the depth was read, the number of items read equals `min(depth, total_count)`, and every item has the required fields. Otherwise the pass is incomplete for that period.
- If the tool used summarizes, truncates or omits results or fields, the pass is incomplete: the period stays unchecked, report the limitation and the tool, and do not infer missing results or values. Request smaller pages if that yields complete results.
- Record `total_count` and items read for each pass; a total above the depth is reported as a bounded search.
- Established results that are already recorded (in `items` or `historical_ids`) are counted as repeated observations and are not re-verified unless due; report how many results read were not already recorded.

## Curated lists
- List changes over P: in the metadata clone, process the commits in `git log --first-parent --since=<P start> --until=<P end> <default branch> -- <list files>` one by one; commits reachable only through merged branches are not processed separately. For each commit, compare the repository IDs (framework Item identity) linked in the list files immediately before it (its first parent) and after it; IDs linked only after it are that commit's additions. The additions over P are the union over all its commits, so a repository added and later removed within P is included; a comparison of only P's start and end does not satisfy this.
- A list repository that cannot be cloned or read makes the method unchecked for P.

## Verification
Retrieve full metadata only for relevant candidates and due re-verifications, never for every search result.
- **Identity and status:** `id` (`repo_id`), `full_name`, `fork`, `archived`, `license.spdx_id`, `created_at`, `pushed_at` and `default_branch` from the full repository metadata (MCP `repo:` search with full output, or `GET /repos/{owner}/{repo}`). The `id` must match the stored `repo_id` for recorded items.
- **Latest release:** the newest non-draft release from field-filtered `list_releases`, with its `published_at`.
- **Latest tag:** when there is no release, or a newer tag must be checked, take tags from `git ls-remote --tags` and dates from the metadata clone (precise). Without Git, use `list_tags` and `get_commit` for each tag on the first page, and state that the tag list is not guaranteed to be ordered by date. A lightweight tag's date is its commit's date.
- **Renamed or transferred:** a `repo:` search on the stored name returns nothing while Git still resolves the URL. Find the new name, confirm its `id` equals the stored `repo_id`, then report the rename.
- **Deleted or private:** a `repo:` search (or API request) finds nothing and `git ls-remote` reports the repository not found. Confirm on one later run before moving the item to `historical_ids`.
