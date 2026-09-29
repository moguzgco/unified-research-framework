# URF Research Contract

Common contract for all URF research. It defines what research is and the rules every research agent follows. It is not executed or selected on its own: every run follows exactly one execution contract (section 1), which defines how the run proceeds, which further files it reads and which outputs it writes. A private project holds read-only copies of these contracts in `framework/`. Design rationale lives in `URF_ARCHITECTURE.md`, which is not loaded at runtime.

Research, in URF, means discovering, screening, verifying and reporting information within a stated scope, with every finding backed by evidence from original sources (section 5).

## 1. Files and load order

**Execution contract.** Every run's invocation selects exactly one execution contract with the line `Contract: <name>`. Supported contracts:

- `continuous` → `framework/CONTINUOUS-AGENT-CONTRACT.md`

This contract is always loaded with the selected one and is never selected on its own. There is no default. A missing `Contract:` line, an unlisted name, or more than one `Contract:` line is a pre-execution configuration error: the run stops before any research, changes no research state, creates or modifies no persisted report, and states the error only in its run output. The fatal-error rule (section 7) does not apply.

Each run reads, in this order:

1. `framework/RESEARCH-CONTRACT.md` (this file).
2. The selected execution contract.
3. `framework/FRAMEWORK.md` and `framework/SOURCES.md`.
4. `PROJECT.md` and, if present, `SOURCES.md`.
5. Any further files the execution contract requires.
6. Only the `framework/sources/*.md` guides for sources used in this run.

Files in `framework/` are read-only for the research agent. The research agent writes only the outputs its execution contract defines.

Optional context reuse: previously loaded instructions may be reused only when the agent can confirm the files are unchanged (for example, the same Git commit for those paths). Files the execution contract requires to be read fresh are always read fresh. When in doubt, reload. Correct execution never depends on retained context.

## 2. Precedence

For configurable settings (sources, budgets, procedures, reporting preferences):

`PROJECT.md` / `SOURCES.md` > `framework/FRAMEWORK.md` / `framework/SOURCES.md` > defaults in this contract and the execution contract.

An explicit project value is an override even when it equals the parent value. At the same layer, an explicit exclusion wins over an inclusion; note the inconsistency in the report. The invariants in section 3, and those the execution contract declares, are not configurable.

## 3. Invariants

No framework or project setting may disable or weaken these. Execution contracts may add invariants of their own.

- **I1 Evidence.** Every reported finding links to at least one source the agent actually accessed. Verify against original sources as the framework requires. Anything not verified is reported as an unverified lead, not a finding.
- **I2 Truthful reporting.** Report actual coverage, failures and partial runs. Never pad findings or claim checks that were not performed.
- **I3 Genuine dates.** Reports and any other outputs use the actual execution date. Never backdate or fabricate a dated report.
- **I5 Continuity.** Never delete historical reports.
- **I6 Persist before notifying.** Send email only after the run's outputs have been committed and pushed successfully.
- **I7 Source scope.** Never use an effective excluded source for discovery or verification.

## 4. Effective sources

Compute at the start of each run and list the result in the report.

1. **Allowed.** If the project `Allowed` section says `Mode: only`, use the project list alone; an empty `Mode: only` list is a configuration error: report it and use the framework list unchanged. Otherwise (`Mode: add`, the default) combine framework and project entries; if the framework list is empty, discovery stays unrestricted and the project entries are always included. A missing or empty project section does not erase framework entries.
2. **Excluded.** Combine framework and project exclusions. A project entry in `Allowed` overrides a framework exclusion of the same source; a project exclusion overrides a framework inclusion.
3. Remove effective exclusions from effective Allowed.
4. An empty effective Allowed list, or the unrestricted case in step 1, means discovery is unrestricted except for exclusions. Otherwise discovery is restricted to the effective Allowed list.
5. **Matching.** An entry covers its domain and all subdomains, or, for a URL, that path and below. When entries overlap, the more specific entry wins; at equal specificity the rules above apply.
6. **Verification links.** Following original-source links outside the Allowed list is permitted only when the effective setting is `permitted` (default: `not permitted`). Exclusions still apply.

## 5. Research steps

Execution contracts sequence these steps and may add their own.

- **Record** the execution date, available tools and permissions. If Git push access is unavailable, stop and report; do not research without a way to persist.
- **Discover** candidates within effective sources and budget.
- **Screen** candidates against scope and relevance, and against anything else the execution contract adds.
- **Verify** relevant candidates against original sources.
- **Analyze** relevance and extract the framework's target fields.
- **Report** (section 6), **validate** (section 7), **persist and notify** (section 8).

A finding is verified as the framework requires; anything else is an unverified lead (I1). Candidates are identified and deduplicated by the framework's stable ID.

## 6. Reports

The execution contract defines report files, sections and classifications. In every report, each item lists its ID, title, source link(s), relevant dates, a short evidence summary and its classification. Empty sections say "None".

## 7. Failures and validation

- **Source failure** — record it in the report and continue with other sources. Status: partial.
- **Operation failure** — within a source, continue independent operations after one fails while the budget permits. Report each operation as complete, incomplete (attempted but not fully retrieved) or unattempted (not run, with the reason). Candidates from an incomplete operation may be kept as unverified leads; the operation stays incomplete.
- **Fatal error** — write a failed report with the reason; commit and push the report if possible.
- **Before committing** — every finding has a link; the report date is the execution date.
- **Push failure** — report it in the run output and send no email.

## 8. Persistence and email

- Commit the run's outputs with the commit message format the execution contract defines. Push to `main` and confirm success.
- Email only when configured in `PROJECT.md` and a delivery tool is available, and only after a confirmed push. This applies to complete, partial and failed runs alike. Content: the run status, a short summary and the report's repository path or link.
- Never resend automatically. A failed or uncertain delivery is stated in the run's final output as a notification failure, separate from research status. No commit is made solely to record delivery status.
