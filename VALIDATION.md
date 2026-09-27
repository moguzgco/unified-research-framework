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
- [ ] `state.json` records stable IDs and baseline progress; report and state are pushed.

**V2 Overlapping incremental**
- [ ] A run overlapping V1's coverage reports no previously recorded item as new.
- [ ] IDs are stable; repeated observations are classified as such.
- [ ] Checkpoints advance only over verified coverage.

**V3 Material change and partial failure** (throwaway branch)
- [ ] Altering the recorded change indicators of one or two items produces material-change findings with evidence; unchanged items are not flagged.
- [ ] Making one source unavailable (for example, a temporary exclusion) yields status `partial`, discloses the gap and leaves that source's checkpoint unchanged.

**V4 Reporting and persistence**
- [ ] Report follows the contract skeleton; dates are genuine; `state.json` parses.
- [ ] Commit and push are confirmed before any email.
- [ ] Email (if used) goes only to the maintainer during testing; a failed delivery is reported without a resend or extra commit.

**V5 Source overrides**
- [ ] A project exclusion of a framework source prevents discovery and verification from it.
- [ ] A project addition is used alongside framework sources (`Mode: add`).
- [ ] `Mode: only` restricts discovery to the project list.
- [ ] The verification-links setting is respected.

**V6 Periodic synthesis dry run**
- [ ] Built only from existing daily reports; every finding links to its daily report and original source.

## Review

- [ ] Evidence quality, coverage honesty and the invariants in `RESEARCH-CONTRACT.md` section 3.
- [ ] Maintainer approval recorded before a schedule is enabled or a framework is published.

## Re-test after propagation

Run V2 plus each test covering the changed behavior, in a test repository or on temporary copies.
