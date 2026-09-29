# URF Deep Research Agent Contract

Execution contract for Deep research: manual, bounded research on a stated subject and purpose, broad in discovery and deep in evidence, ending in one comprehensive report. A run selects it with `Contract: deep` (common section 1). It follows `RESEARCH-CONTRACT.md` (the common contract); every rule there applies. This file adds only the Deep rules. A private project holds a read-only copy at `framework/DEEP-AGENT-CONTRACT.md`.

"Deep" describes research intent — following promising findings further and verifying them more thoroughly — not a traversal algorithm.

## 1. Brief, files and outputs

The invocation states, in natural language, below the `Contract: deep` line:

- **Subject** — what to research.
- **Purpose** — what the result will be used for, for example general research, a baseline or reference landscape for a project, or a higher-effort reference result for accuracy comparison.
- **Constraints** (optional) — scope limits, sources to favour or avoid within the effective sources, effort bounds such as time, number of searches or depth, and whether to send a notification (section 6).

A missing subject or purpose is a configuration error, handled as in common section 1.

The subject and purpose set what the run researches within the framework's domain. Framework and project rules for sources, verification and relevance still apply (common sections 2 and 4); invocation constraints may narrow them but not widen them.

Deep research reads no further files (common section 1, item 5). It does not read `state.json` or existing reports, unless the invocation explicitly asks to compare with them; it then reads them without changing them.

The research agent writes only its Deep report (section 5).

## 2. Invariants

Not configurable, in addition to common section 3.

- **D1 Isolation.** A Deep run writes only its own Deep report. It never creates or changes Continuous state (`state.json`, including coverage and checkpoints), existing reports, or the operational state of any other execution contract.

## 3. Process

The common research steps (common section 5), sequenced for a brief:

1. **Understand the brief** and record it, with the execution date, tools and permissions (*Record*).
2. **Plan** the research questions the brief implies.
3. **Discover broadly** within effective sources and the brief's constraints (*Discover*).
4. **Screen** candidates for relevance to the brief (*Screen*).
5. **Follow promising paths** — related sources, references and dependencies of relevant findings — and discover and screen again where useful.
6. **Verify** relevant findings against original sources (*Verify*), gathering enough evidence to explain each one.
7. **Analyze**, and **compare** findings where comparison serves the purpose. **Rate** findings only against criteria the framework or project provides, and name the criteria used.
8. **Synthesize** the answers to the research questions.
9. **Report** (section 5), validate (common section 7), persist, and notify if requested (common section 8; section 6).

## 4. Stopping

Deep research is bounded. Stop when an effort bound in the invocation is reached, or when further exploration yields little additional relevant information. The report states why exploration stopped.

Budgets defined for Continuous research (discovery, verification and re-verification budgets per run or baseline) do not apply to Deep research. Framework or project limits apply only when they are stated as general research constraints.

Deep research has no coverage periods, checkpoints or resumption: a later Deep run starts from its own brief.

## 5. Report

- File: `reports/deep/YYYY-MM-DD-<slug>.md`, where `<slug>` is a short lower-case, hyphenated form of the subject. If that path exists, use the next free numeric suffix (`-2`, `-3`, …). `reports/deep/` is created when first needed.
- Classifications: **Finding** (verified) or **Unverified lead** (I1).
- Status: `complete` — the planned research questions were addressed; `partial` — some were not, because of effort bounds or failures; `failed` — a fatal error after research began (common section 7).

```markdown
# <Project> — Deep report YYYY-MM-DD: <subject>

Run: <ISO timestamp> · Contract: deep · Status: complete | partial | failed

## Brief
Subject, purpose and constraints as given.

## Method
Research questions; effective sources; what was explored and which paths were followed; the status of each operation actually attempted (common section 7). Operations that were never part of the plan are not listed as unattempted.

## Findings
## Comparisons and ratings
## Unverified leads and open questions
## Limitations and stopping reason
```

Each finding follows common section 6 and adds a concise explanation of what it is and why it matters for the purpose. Comparisons and ratings name their criteria; if none apply, the section says "None".

## 6. Persistence

- Commit message: `research: YYYY-MM-DD deep <status> <slug>`.
- Email: only when the invocation explicitly requests notification and common section 8 otherwise permits it. A project's email configuration alone does not trigger Deep email.
