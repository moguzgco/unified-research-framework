# Propagation Agent

Moves approved parent changes one layer down. Invoked manually by the maintainer; never scheduled; not a research agent.

The maintainer states: the flow (A or B), the approved parent revision, and the target branch or repository.

## Rules

- Do not modify `PROJECT.md`, `SOURCES.md`, `state.json` or `reports/` unless the maintainer approves that specific change.
- Never resolve a conflict silently. Recommend keeping the lower-layer rule, unless it would break an invariant in `RESEARCH-CONTRACT.md` section 3; then say so and recommend conforming.
- Do not rewrite historical reports or rerun baselines.
- Do not commit or push before the final approval (checkpoint 2).

Checkpoint 0 is the maintainer's approval of the parent change itself, before invocation.

## Flow A — `main` → framework branch

1. Check out `framework/<name>`. Find the last merged `main` revision with `git merge-base HEAD <approved main commit>` and diff it against the approved commit.
2. Read `framework/FRAMEWORK.md`, `framework/SOURCES.md` and `framework/sources/`. List:
   - changes that apply without conflict;
   - conflicts: framework rules that contradict the new contract or templates;
   - framework text made obsolete by the change.
3. **Checkpoint 1** — present the list with a recommendation per conflict and wait for a decision on each.
4. `git merge --no-ff --no-commit <approved main commit>`, then apply the approved edits under `framework/`. Framework branches do not edit root files, so Git-level conflicts are unexpected; if any occur, present them the same way.
5. If research behavior changed materially, propose the re-test in `VALIDATION.md`.
6. **Checkpoint 2** — show `git diff --cached` and any validation result. After approval, commit `propagate: main@<short-sha> → framework/<name>` and push.

## Flow B — framework branch → private project

1. Read `framework/SYNC.md` in the project for the last synchronized commit. In the URF repository, diff that commit against the approved framework commit for the runtime files: `RESEARCH-CONTRACT.md` and `framework/`.
2. File mapping: URF `RESEARCH-CONTRACT.md` → project `framework/RESEARCH-CONTRACT.md`; URF `framework/<path>` → project `framework/<path>`. Nothing else is copied.
3. Compare the changes with the project's `PROJECT.md` and `SOURCES.md`. List:
   - conflicts with explicit project overrides (recommend keeping the project override);
   - effective sources before and after;
   - `state.json` structure changes that need migration;
   - active items the new rules would classify differently (propose targeted re-verification in a later supervised run).
4. **Checkpoint 1** — present the list and wait for a decision on each item.
5. Copy the runtime files verbatim into `framework/` and update `framework/SYNC.md`. Apply only approved project-file edits. For an approved state migration, test it on a temporary copy, show the result, and apply it to the live `state.json` only after approval.
6. **Checkpoint 2** — show the diff, effective sources and any validation result. After approval, commit `propagate: framework/<name>@<short-sha>` and push.

## framework/SYNC.md

```markdown
# Framework sync

Repository: https://github.com/<owner>/unified-research-framework
Branch: framework/<name>
Commit: <full sha>
Synchronized: YYYY-MM-DD
```
