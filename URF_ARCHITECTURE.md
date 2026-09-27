# Unified Research Framework — Architecture and Blueprint

This document is the agreed design reference for a reusable, Markdown-first research framework, informed by two existing projects:

1. Repository Scout — discovers and monitors public software repositories. Its initial AI/LLM research project is currently undergoing supervised validation.

2. Job Scout — discovers and monitors job opportunities. The original research-agent blueprint was extracted from this project, but the project has evolved since then and contains additional architectural decisions.

Existing project documentation, the original research-agent blueprint and the architecture diagram are supporting references when available. They are not authority over the decisions in this document. Do not redesign either existing project as part of implementing URF.

**Objective:** Establish a unified blueprint and minimal reusable templates for additional specialized research frameworks without new software infrastructure.

The blueprint should capture shared architecture, research procedures, configuration conventions, execution rules and validation requirements.

It is a design-time resource, not another mandatory instruction layer loaded on every recurring research run. One individual maintains the system; parent frameworks change infrequently. Prefer straightforward Markdown and Git operations over platform-style engineering.


## 1. Three-layer architecture

LAYER 1 — UNIFIED RESEARCH FRAMEWORK

Maintained on the public Git `main` branch. Defines common architectural principles, not specific external research websites or source lists:

- Agent execution and scheduling.
- Discovery, verification and analysis.
- Evidence quality and source traceability.
- Initial historical research and incremental discovery.
- Deduplication and material-change detection.
- Daily reporting and periodic synthesis.
- Git-based persistence.
- Optional context persistence.
- Research budgets and failure handling.
- Supervised validation and approval.

LAYER 2 — SPECIALIZED RESEARCH FRAMEWORKS

Each framework specializes the unified blueprint for a particular type of information and lives on a framework branch originating from `main` (for example, `framework/repo-scout`). Approved framework revisions can be used to initialize separate private project repositories.

Examples:

Job Scout
- Target: job opportunities.
- Sources: LinkedIn, Indeed, employer career pages and other job portals.
- Specialized rules: job identity, duplicate postings, eligibility, compensation, application requirements and listing changes.

Repository Scout
- Target: public software repositories.
- Sources: GitHub, GitLab, Bitbucket, Codeberg and other Git hosts.
- Specialized rules: repository identity, forks, mirrors, licenses, releases, activity and material changes.

News Scout
- Target: announcements, articles and developments.
- Sources: official company websites, product announcements and news publishers.
- Specialized rules: publication dates, original reporting, corrections, updates and repeated coverage of the same event.

Peer Scout
- Target: public activity involving people, organizations and competitors.
- Sources: public social media, official profiles, company websites and public communities.
- Specialized rules: entity identity, attribution, public-source verification and changes in observed activity.

These are examples, not a fixed list.

Each specialized framework defines its own target identity, discovery methods, source-specific verification, deduplication and meaningful-change criteria.

LAYER 3 — DOMAIN-SPECIFIC RESEARCH PROJECTS

Each specialized framework supports multiple independently configured research projects, each in its own private Git repository. A project starts from an approved specialized framework and owns its individual research configuration and history.

Examples:

Job Scout:
- Full-time opportunities.
- Freelance and contract opportunities.

Repository Scout:
- AI/LLM repositories.
- Machine learning.
- Bioinformatics.
- Embedded systems.
- Web frameworks.

News Scout:
- Finance.
- Claude.
- GPT.

Peer Scout:
- Public social media research.
- Competitor and entrepreneur research.

Each project defines its own scope, preferences, relevance criteria, enabled sources, exclusions, schedule, budget, state and reports. Explicit private-project specifications override conflicting framework defaults; approved changes to parent layers are synchronized downward only through the manually invoked propagation procedure.

Creating another project under an existing specialized framework should normally require only:

1. Copying the private-project template and configuring PROJECT.md.
2. Attaching the project to a Claude recurring agent with access to its specialized framework.
3. Configuring its schedule after validation.

Creating a new private research subject should not require changes to its specialized framework unless the target information type introduces genuinely new requirements.


## 2. Mandatory architectural constraints

MARKDOWN-FIRST

Use Markdown instructions, configuration and agent capabilities.

Do not introduce mandatory application code, servers, databases, deployment infrastructure, custom schedulers or background services.

Ordinary web research should be sufficient wherever practical.

APIs, CLIs and MCP integrations may optionally improve access to particular sources, but the framework must not depend on any specific integration.

CLAUDE EXECUTION

Claude recurring agents perform research using their available tools.

Each agent follows its specialized framework and private-project configuration.

The unified blueprint is used to design specialized frameworks. It does not need to be loaded during recurring research execution.

GIT PERSISTENCE

Git is the sole authoritative persistent storage.

Each private project maintains:
- PROJECT.md.
- A lightweight state.json.
- Dated daily reports.
- Periodic synthesis reports.

Reports preserve research history and original source references.

State is a compact index for deduplication, previous observations and execution progress: active items, compact historical records, pending leads, the fixed baseline window, per-source coverage dates and optional source-native checkpoints when useful for that research type. Detailed evidence and history belong in dated reports and Git. State is not a database or duplicate report archive.

Do not introduce additional persistent storage systems.

SINGLE-AGENT EXECUTION — NO CONCURRENCY ENGINEERING

Each private research project has exactly one assigned recurring agent and one research job.

Only that research agent writes research state and reports to its private Git repository during scheduled execution. The maintainer may separately invoke the Propagation Agent for approved instruction updates; this is not concurrent research execution.

Runs are sequential and do not overlap.

Different projects have separate private repositories and independent writable state.

These are deliberate architectural assumptions.

Do not design for concurrent writers, race conditions or overlapping executions.

Do not introduce:
- Locks or distributed coordination.
- Queues or worker orchestration.
- Optimistic concurrency control.
- Complex Git conflict-resolution procedures.
- Additional synchronization storage.
- Retry infrastructure for hypothetical concurrency scenarios.

Use straightforward Git operations.

If the execution environment cannot guarantee sequential runs, identify this as an environment requirement rather than designing concurrency infrastructure.

Do not spend time or tokens analyzing hypothetical multi-agent concurrency scenarios.

OPTIONAL CONTEXT PERSISTENCE

Support optional reuse of previously loaded framework instructions, project configuration and source guides between recurring executions.

Reuse is permitted only when the agent can confirm the relevant files have not changed.

Always read the latest state.json and the previous reports needed for the current run.

If context persistence is unavailable, uncertain or truncated, load the necessary files normally.

Correct execution must never depend on persistent conversational context.

Do not introduce memory services, vector databases, embeddings, retrieval indexes or custom caching infrastructure solely for context persistence.


## 3. Initial baseline and incremental research

The first execution of a new research project should establish an extended historical baseline.

Its purpose is to capture important existing items and past developments that ordinary scheduled runs might otherwise miss.

The baseline window and budget are configurable in PROJECT.md. Frameworks supply default budgets; projects may override them, and supervised tests may use temporary overrides. Start with conservative limits, then increase them when coverage and accuracy justify it.

Prioritize relevance and significant historical findings rather than exhaustive collection.

A longer baseline may be divided into a small number of supervised runs if necessary. Do not increase complexity or introduce a separate orchestration system.

After the baseline, scheduled runs should perform incremental research.

Use previous reports and state.json to identify previously researched items and periods.

Avoid repeatedly inspecting unchanged sources or rediscovering previously processed findings. Retain compact historical identifiers even when items are no longer active. When a source is only partially checked, do not silently advance its discovery checkpoint beyond verified coverage.

Each specialized framework defines appropriate source-specific change indicators.

Examples:

Repository Scout:
- Repository identity.
- Commit history.
- Release tags.
- Archived status.
- Other available repository change indicators.

Job Scout:
- Publication dates.
- Listing identifiers.
- Previously recorded opportunities.
- Listing updates or removal.

News Scout:
- Publication timestamps.
- Article updates.
- Original announcement dates.
- Previously covered events.

Peer Scout:
- Public post identifiers.
- Publication timestamps.
- Previously observed public activity.

Use these indicators to prioritize new or changed information.

Do not permanently exclude a source merely because it was previously inspected.

Previously observed items remain eligible for meaningful-change detection when new evidence appears or their configured verification interval is reached.

Record only the information necessary for incremental research in the existing state and reports.

Do not introduce separate indexes, databases, crawlers or additional infrastructure.

Keep the baseline and incremental-discovery rules lightweight and configurable.


## 4. Common research workflow

The general execution procedure is:

1. Load the specialized framework and private-project configuration.

2. Check the execution date, available tools, permissions and previous research state.

3. Determine whether this is an initial baseline or an incremental scheduled run.

4. Resolve the effective framework-plus-project source configuration; discover candidates within its allowed sources, exclusions and research budget.

5. Screen candidates against scope, previous observations and available change indicators.

6. Verify relevant candidates against reliable original sources.

7. Analyze relevance and extract target-specific information.

8. Compare findings with previous observations.

9. Classify first observations, verified new items, material changes and repeated observations, where applicable.

10. Generate a dated daily report.

11. On configured reporting days, synthesize the relevant daily reports into a periodic report.

12. Validate and persist the report and updated state in Git, then confirm successful push.

13. If configured and an authorized delivery tool is available, send email only after successful Git persistence. Treat uncertain or failed delivery separately from research success. Never resend failed or uncertain emails automatically; report the delivery failure in the run output without an additional commit solely to record delivery status.

The specialized framework determines the exact identity rules, evidence requirements and meaningful-change criteria for its target type.

Every execution produces a daily report, including partial and failed runs.

Failed runs preserve the last successful research state.

Partial runs may retain verified findings while disclosing incomplete coverage. Do not advance a source checkpoint for work that was not completed.

Periodic reports use daily reports as their primary source and link to original findings.

Do not pad reports to reach an arbitrary number of findings.

Use genuine execution dates. Never fabricate dated research reports.


## 5. Separation of responsibilities

UNIFIED BLUEPRINT

Defines how to design and validate a specialized research framework.

It contains common architectural contracts and decisions every specialized framework must address, but no specific external source references. It is maintained on `main`.

SPECIALIZED FRAMEWORK

Defines how to research a particular type of information.

It supplies source guides, default source configuration, identity and deduplication rules, verification procedures, material-change criteria and specialized reporting requirements. It is maintained on its own framework branch.

It incorporates the necessary common instructions and remains independently executable.

PRIVATE PROJECT

Defines the subject being researched, exact sources, relevance preferences, exclusions, schedule, research budget and any project-specific reporting preferences. Explicit project specifications override conflicting framework defaults.

It owns its state and research history.

Avoid duplicating the same instructions across these levels.

The unified blueprint must not become a runtime dependency.


## 6. Supervised validation

Every new specialized framework should be validated before recurring execution is enabled.

Prefer a small number of inexpensive supervised tests:

1. Limited baseline discovery, including representative historical findings.

2. Overlapping incremental run to verify deduplication and historical continuity.

3. Controlled material-change detection using temporary copies of research state, where applicable.

4. Periodic synthesis dry run using existing daily reports.

5. Review of source failures, incomplete coverage, evidence quality and report accuracy.

Use temporary budget overrides to keep tests economical without sacrificing the verification needed to establish correctness.

Do not require real-world changes to occur during testing.

Do not modify real research state for controlled tests.

Preserve actual execution dates.

Require explicit approval before enabling recurring execution or publishing a new framework.


## 7. Source configuration and inheritance

URF defines *how* source configuration is interpreted but contains no external research source references. A specialized framework may define default source types, specific allowed sites and exclusions. A private project may add to or explicitly override those defaults in an optional `SOURCES.md` with `Allowed` and `Excluded` sections; framework defaults apply when the project does not override them.

- Combine the framework and private-project configurations. On a conflict, the project's explicit inclusion or exclusion takes precedence over the framework rule. At the same layer, an explicit exclusion wins over an inclusion unless the maintainer resolves the inconsistency.
- A missing or empty project Allowed section does not erase framework Allowed entries. When no layer restricts Allowed sources, discovery is unrestricted except for effective exclusions. A nonempty effective Allowed list restricts discovery to those sources.
- A project may narrow discovery with `Mode: only` in its `Allowed` section: its Allowed list then replaces the framework Allowed list instead of extending it. The default, `Mode: add`, extends the framework list.
- Distinguish discovery sources from original-source verification links. A framework or project may explicitly permit following verification links outside the discovery Allowed list; explicit effective exclusions still apply.
- Changing project sources should not erase historical reports. Newly enabled sources may require a source-specific historical baseline; disabled sources cease discovery without losing recorded history.
- Every project records a compact per-source coverage date in `state.json`, advanced only over verified coverage, so partial runs never create missed discovery windows. Source-native checkpoints (cursors, last IDs) are optional and framework-specific.

The same lower-layer precedence applies to configurable research procedures, budgets and reporting preferences. Preserve explicit overrides even when their current value happens to match the parent. Any conflict discovered during propagation is presented for approval rather than silently resolved. Fundamental evidence integrity and truthful reporting are common research contracts, not defaults to be silently discarded.


## 8. Git hierarchy and manual propagation

Git organization:

- URF: public `main` branch containing shared research contracts and minimal templates.
- Specialized frameworks: branches originating from `main`, with domain-specific research instructions and defaults.
- Private projects: separate private repositories initialized from an approved specialized-framework revision, with their own configuration, state and reports. Git branches are not privacy boundaries. Each private project keeps a read-only copy of its framework's runtime files in `framework/`, with the synchronized framework repository, branch and commit recorded in `framework/SYNC.md`. Project-specific changes belong in `PROJECT.md` and `SOURCES.md`, never in `framework/`.

A small **Propagation Agent**, instructed by `PROPAGATION.md`, is invoked manually after the maintainer approves changes to URF or a specialized framework. It is not scheduled, continuously running or a research agent.

Its workflow is deliberately short:

1. Compare the approved parent revision with the last parent revision synchronized to the selected descendant branches or private repositories. The maintainer may identify which descendants to update; no elaborate registry is required.
2. Propose applicable instruction/template changes. Remove or replace clearly obsolete inherited instructions where necessary; preserve descendant-owned configuration, state and reports. Synchronize public-framework updates to private repositories selectively rather than indiscriminately merging private histories.
3. Present any conflicts, recommend the lower-layer override by default and **ask the maintainer to choose and approve each resolution** before applying it. Do not silently override conflicting descendant specifications.
4. Apply approved changes. Review resulting instructions and effective sources. For material research-behavior changes, use a small supervised test; for state-structure changes, propose and test any necessary migration on temporary copies and obtain approval before touching live state.
5. Show the final diff and validation outcome. Commit and push only after final approval; record the last synchronized parent commit after successful propagation.

Ordinary updates apply prospectively. Do not rewrite historical reports or automatically rerun the full historical baseline. If changed rules materially affect existing active observations, identify targeted re-verification for a later supervised research run.

Parent changes are made manually by one maintainer and are expected to be infrequent. Do not add automated propagation, complex versioning, migration frameworks, branch synchronization services, continuous monitoring or team-oriented approval infrastructure.


## 9. Minimal implementation and handoff

The first Claude implementation session should read this document and any available Job Scout, Repository Scout, original-blueprint and architecture-diagram references. Existing projects are practical examples, not specifications to copy wholesale. Where older documents conflict with the agreed decisions here, identify the discrepancy and use this document unless the maintainer decides otherwise.

**Stage 1 — Review and plan (no file or Git changes):**

1. Identify only material gaps, contradictions and unnecessary complexity.
2. Propose the minimum URF file layout and responsibilities, avoiding duplicated instructions. The adopted layout is `README.md`, `URF_ARCHITECTURE.md` (this design reference), `RESEARCH-CONTRACT.md`, `PROPAGATION.md`, `VALIDATION.md` and minimal specialized-framework/private-project templates.
3. Explain how a framework branch and a separate private project repository are initialized and how the manual Propagation Agent operates.
4. Present a short implementation plan and stop for explicit approval.

**After Stage 1 approval:** Implement the URF `main` branch, minimal templates and Markdown propagation instructions. Validate the contracts with representative examples. Ask for approval before creating real specialized-framework branches, migrating existing projects, configuring scheduled agents or making external repository changes not already authorized.

**Private-project runtime:** A project normally needs `PROJECT.md`, optional `SOURCES.md`, compact `state.json`, dated daily reports and periodic synthesis reports, together with a read-only `framework/` copy of its specialized-framework runtime instructions. Its scheduled research agent loads the relevant runtime instructions, not the entire URF design repository.

**Scope and priorities:** Research accuracy and source verification first; historical continuity and correct change detection next; efficient execution and token use thereafter. Keep everything maintainable by one developer. One project, one research job per configured daily period, with optional weekly synthesis. No concurrency engineering or continuously running services. Do not implement additional infrastructure merely because a larger production system might need it.
