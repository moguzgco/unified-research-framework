# Unified Research Framework

URF is a Markdown-first framework for independent, specialized research agents run on a schedule by Claude, with Git as the only persistent storage. One maintainer; no servers, databases or custom schedulers.

## Layers

| Layer | Where | Contains |
|---|---|---|
| URF | this repository, `main` | shared research contract, propagation and validation procedures, templates; no external research sources |
| Specialized framework | branch `framework/<name>` of this repository | domain rules and default sources in `framework/` |
| Research project | separate private repository | `PROJECT.md`, optional `SOURCES.md`, `state.json`, `reports/`, read-only `framework/` copy |

Lower layers override configurable parent defaults; the invariants in `RESEARCH-CONTRACT.md` and in the execution contracts cannot be overridden.

## Files

- `URF_ARCHITECTURE.md` — design reference. Not loaded at runtime.
- `RESEARCH-CONTRACT.md` — common research contract copied into every project; not executed on its own.
- `CONTINUOUS-AGENT-CONTRACT.md` — execution contract for Continuous (scheduled, incremental) research, selected with `Contract: continuous`; follows the common contract.
- `PROPAGATION.md` — manually invoked Propagation Agent.
- `VALIDATION.md` — supervised validation checklist.
- `templates/framework/`, `templates/project/` — starting files.

## Create a specialized framework

1. `git switch -c framework/<name> main`
2. Copy `templates/framework/*` to `framework/` and complete it. Do not edit root files on the branch.
3. Validate with `VALIDATION.md` in a disposable test project; approve before use.

## Create a research project

1. Create a new empty private repository (not a fork).
2. Copy `templates/project/*` to its root and create `reports/daily/` and `reports/periodic/`.
3. Copy the runtime files from an approved framework commit into `framework/` and write `framework/SYNC.md` (see `PROPAGATION.md`, Flow B).
4. Complete `PROJECT.md` and, if needed, `SOURCES.md`, recording only values that differ from the framework.
5. Validate, then attach one scheduled Claude task. Example prompt:

   ```
   Run the research project in <owner>/<repository> on branch main.
   Contract: continuous
   Follow framework/RESEARCH-CONTRACT.md exactly. Commit and push results before any email.
   ```

## License

MIT — see `LICENSE`.
