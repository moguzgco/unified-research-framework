# GitHub Source Guide

## Access paths
Confirm at the start of each run which paths work and record them under Coverage. Use whichever tool is available; the framework does not depend on a specific integration.

1. **GitHub MCP server (preferred when available)** — read-only tools only:
   - `search_repositories` — discovery with compact output (`minimal_output: true`); single-repository metadata with the query `repo:{owner}/{repo}` and full output (`minimal_output: false`).
   - `list_releases` with `fields: tag_name, published_at, prerelease, draft` — release dates. Avoid tools that return full release bodies.
   - `list_tags` and `get_commit` (`detail: none`) — tag names and the dates of tagged commits.
   - `get_file_contents` — README, license and list files.
2. **REST API (JSON)** — the same endpoints directly: `GET /search/repositories?q=<query>&sort=stars&order=desc&per_page=<depth>&page=<n>`, `GET /repos/{owner}/{repo}`, `GET /repos/{owner}/{repo}/releases`. Unauthenticated search allows only a few requests per minute.
3. **Git protocol** — `git ls-remote --tags https://github.com/{owner}/{repo}.git`; a metadata-only clone in scratch, `git clone --bare --filter=blob:none https://github.com/{owner}/{repo}.git`, for curated-list history and precise tag and commit dates.
4. **Web pages** — README and documentation text, for purpose and requirements only.

Pace search requests to the path's rate limit and count each request, including each page, against the search budget.

If no path returns structured dates, verification is incomplete: report affected candidates as unverified leads. Tools that summarize pages can misstate dates and versions; take them only from raw API fields or Git output.

## Repository search
- Date qualifiers use whole days: `created:YYYY-MM-DD..YYYY-MM-DD`, `pushed:YYYY-MM-DD..YYYY-MM-DD`.
- Use compact results for discovery. Required fields per item: `full_name`, `id`, `created_at`, `fork` and `archived`. `pushed_at` is not required in discovery results: the established pass's `pushed:P` qualifier already bounds activity, and `pushed_at` is retrieved at verification.
- A result list is complete when `incomplete_results` is false, every page within the depth was read, the number of items read equals `min(depth, total_count)`, and every item has the required fields. Otherwise the pass failed for that period.
- If the tool used summarizes, truncates or omits results or fields, the pass failed: mark the period unchecked, report the limitation and the tool, and do not infer missing results or values. Request smaller pages if that yields complete results.
- Record `total_count` and items read for each pass; a total above the depth is reported as a bounded search.

## Curated lists
- List changes over P: in the metadata clone, `git log --since=<P start> --until=<P end> -p -- <list files>`, reading only added lines.
- A list repository that cannot be cloned or read makes the method unchecked for P.

## Verification
Retrieve full metadata only for relevant candidates and due re-verifications, never for every search result.
- **Identity and status:** `id` (`repo_id`), `full_name`, `fork`, `archived`, `license.spdx_id`, `created_at`, `pushed_at` and `default_branch` from the full repository metadata (MCP `repo:` search with full output, or `GET /repos/{owner}/{repo}`). The `id` must match the stored `repo_id` for recorded items.
- **Latest release:** the newest non-draft release from field-filtered `list_releases`, with its `published_at`.
- **Latest tag:** when there is no release, or a newer tag must be checked, take tags from `git ls-remote --tags` and dates from the metadata clone (precise). Without Git, use `list_tags` and `get_commit` for each tag on the first page, and state that the tag list is not guaranteed to be ordered by date. A lightweight tag's date is its commit's date.
- **Renamed or transferred:** a `repo:` search on the stored name returns nothing while Git still resolves the URL. Find the new name, confirm its `id` equals the stored `repo_id`, then report the rename.
- **Deleted or private:** a `repo:` search (or API request) finds nothing and `git ls-remote` reports the repository not found. Confirm on one later run before moving the item to `historical_ids`.
