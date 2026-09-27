# GitHub Source Guide

## Access paths
Confirm at the start of each run which paths work and record them under Coverage. Use whichever tool is available; the framework does not depend on a specific integration.

1. **REST API (JSON)** — search `GET https://api.github.com/search/repositories?q=<query>&sort=stars&order=desc&per_page=<depth>`; repository `GET /repos/{owner}/{repo}`; releases `GET /repos/{owner}/{repo}/releases?per_page=5`. Unauthenticated search allows only a few requests per minute: pace requests and count each against the budget.
2. **Git protocol** — `git ls-remote --tags https://github.com/{owner}/{repo}.git` for tags; a metadata-only clone in scratch, `git clone --bare --filter=blob:none https://github.com/{owner}/{repo}.git`, for tag and commit dates and curated-list history.
3. **Web pages** — README and documentation text, for purpose and requirements only.

If no path returns structured dates, verification is incomplete: report affected candidates as unverified leads. Tools that summarize pages can misstate dates and versions; take them only from raw API fields or Git output.

## Repository search
- Date qualifiers use whole days: `created:YYYY-MM-DD..YYYY-MM-DD`, `pushed:YYYY-MM-DD..YYYY-MM-DD`.
- A result list is complete when `incomplete_results` is false, the number of items read equals `min(depth, total_count)`, and each item has `full_name`, `id`, `created_at`, `pushed_at` and `fork`. Otherwise the pass failed for that period.
- If the tool used summarizes, truncates or omits results or fields, the pass failed: mark the period unchecked, report the limitation and the tool, and do not infer missing results or values. Request smaller pages if that yields complete results.
- Record `total_count` and items read for each pass; a total above the depth is reported as a bounded search.

## Curated lists
- List changes over P: in the metadata clone, `git log --since=<P start> --until=<P end> -p -- <list files>`, reading only added lines.
- A list repository that cannot be cloned or read makes the method unchecked for P.

## Identity and status
- `repo_id`, `full_name`, `fork`, `archived`, `license.spdx_id`, `created_at` and `pushed_at` come from the repository API response. A request that redirects to another `full_name` indicates a rename or transfer.
- Deleted or private: `git ls-remote` reports the repository is not found and the API returns 404. Confirm on one later run before moving the item to `historical_ids`.
- Latest tag: the newest tag by creation date from the metadata clone, cross-checked with `git ls-remote --tags`.
