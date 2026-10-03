# Supervised Validation

Required before enabling a schedule for a new framework or project, and after propagation that materially changes research behavior.

- Run in a disposable private test repository, or a throwaway branch of one. Never modify real project state.
- Use temporary budget and window overrides in the test repository's `PROJECT.md`.
- Use actual execution dates. Do not wait for real-world changes; simulate them in temporary state.
- Record results in the test repository's reports and summarize pass or fail per test for the maintainer.

## Before testing

- [ ] Web research, Git push and (if used) email tools are available to the agent.
- [ ] Effective sources computed and reviewed.

## Tests

**V1 Baseline**
- [ ] Limited window produces representative historical findings.
- [ ] Each finding is verified and linked to its original source.
- [ ] `state.json` records stable IDs, the fixed baseline window and per-source coverage; an interrupted baseline resumes from that coverage.
- [ ] Report and state are pushed.

**V2 Overlapping incremental**
- [ ] A run overlapping V1's coverage reports no previously recorded item as new.
- [ ] IDs are stable; repeated observations are classified as such.
- [ ] Older items seen for the first time are classified as first observations, not new.
- [ ] Coverage advances only over verified periods.
- [ ] A run during day D searches and covers date-bounded sources only through the last complete day (D−1, or the framework's time zone); no `covered_through` or `baseline.window.to` equals D.
- [ ] A later run, after D has fully elapsed, searches D before advancing coverage past it; checkpoints and the `state.json` format are unchanged.

**V3 Material change, reappearance and partial failure** (throwaway branch)
- [ ] Altering the recorded change indicators of one or two items produces material-change findings with evidence; unchanged items are not flagged.
- [ ] Re-adding a `historical_ids` entry's item to discovery compares it with the stored record; it is reactivated only on verified evidence.
- [ ] Making one source unreachable (for example, an Allowed test source at an unreachable address) yields status `partial`, discloses the gap and leaves that source's coverage unchanged.
- [ ] The next run searches the uncovered period before advancing that source's coverage.

**V4 Reporting and persistence**
- [ ] Report follows the contract skeleton; dates are genuine; `state.json` parses.
- [ ] Commit and push are confirmed before any email.
- [ ] Email (if used) goes only to the maintainer during testing; a failed delivery is reported without a resend or extra commit.

**V5 Source overrides**
- [ ] A project exclusion of a framework source prevents discovery and verification from it.
- [ ] A project addition is used alongside framework sources (`Mode: add`).
- [ ] `Mode: only` restricts discovery to the project list; an empty `Mode: only` list is reported as a configuration error and the framework list is used unchanged.
- [ ] The verification-links setting is respected.

**V6 Periodic synthesis dry run**
- [ ] Built only from existing daily reports; every finding links to its daily report and original source.

**V7 Contract selection**
- [ ] `Contract: continuous` loads `RESEARCH-CONTRACT.md` and `CONTINUOUS-AGENT-CONTRACT.md`; the V1–V6 runs use it.
- [ ] `Contract: deep` with a subject and purpose loads `RESEARCH-CONTRACT.md` and `DEEP-AGENT-CONTRACT.md`; the run writes only its report under `reports/deep/` and leaves `state.json` and all other reports unchanged.
- [ ] Each invalid invocation — no `Contract:` line, an unsupported name (for example `Contract: unknown`), and two `Contract:` lines — stops before any research and states the configuration error only in the run output.
- [ ] After each invalid invocation, the test repository is unchanged: no change to `state.json` or `reports/`, no new report, no commit, push or email.

## Review

- [ ] Evidence quality, coverage honesty and the invariants in `RESEARCH-CONTRACT.md` section 3 and `CONTINUOUS-AGENT-CONTRACT.md` section 2.
- [ ] Maintainer approval recorded before a schedule is enabled or a framework is published.

## Re-test after propagation

Run V2 plus each test covering the changed behavior, in a test repository or on temporary copies.
