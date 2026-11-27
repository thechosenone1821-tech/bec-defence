# AGENTS.md — Instructions for AI Agents working on RAKSHA

> **Audience:** any AI (this file is written for LLMs, autonomous agents and
> human engineers who think like them).
> **Last updated:** 2026-11-26 · **Living document** — keep it true.
> **Phase 1 docs-only freeze, Phase 2 code layout, Phase 3 contract spine,
> Phase 4 Citizen consolidation and Phase 5 MessageGuard single-source recorded:**
> see `PHASE1_ARCHITECTURE_FREEZE.md`, `PHASE2_CODE_LAYOUT.md`,
> `PHASE3_CONTRACT_SPINE.md`, `PHASE4_CITIZEN_CONSOLIDATION.md` and
> `PHASE5_MESSAGEGUARD_SINGLE_SOURCE.md`.

You are acting as a senior engineer on a two-app defence ecosystem for India
(RAKSHA Citizen + RAKSHA Sentinel). Read in this order before touching
anything:

1. `raksha/README.md` — orientation
2. `raksha/CONTEXT.md` — full project context, heritage, principles
3. `raksha/PROBLEM_STATEMENT.md` — the mission, soberly stated
4. `raksha/ARCHITECTURE.md` — the design you are implementing
5. `raksha/BUILD_GUIDE.md` — sequence and conventions
6. `raksha/ROADMAP.md` — where the current effort fits
7. `raksha/CHANGELOG.md` — what already happened, why

---

## 1. Non-negotiable operating rules

1. **Fail closed, always.** If you don't know, the safe action is the answer.
2. **Never weaken a safety rail** (Governor, ledger, dry-run, signature
   checks, canary semantics) to make a demo smoother. Escalate to the
   maintainer instead.
3. **No invented facts.** Any statistic, incident, or law you cite must
   either exist in `CONTEXT.md §5` with a status flag, or carry an inline
   `[VERIFY]` + source pointer. Printing a guess as a fact is the one
   unforgivable error in this project.
4. **No real-world offense.** RAAVAN executes inside sandboxes only. If a
   task seems to require pointing something nasty at a real target, stop and
   tell the maintainer.
5. **Tests or it didn't happen.** New behavior ships with pytest coverage
   in the same commit.
6. **Docs are part of the deliverable.** Update `CHANGELOG.md` and any
   doc you invalidate. Stale docs are bugs, not debt.
7. **Secrets never enter the repo** — not "temporarily", not base64'd.
8. **One doctrine.** Citizen and Sentinel stay on the shared spine
   (graph + ledger + Governor). If your task breaks that, the task is wrong;
   say so rather than fork the architecture silently.

## 2. Workflow conventions

- Branch: `arena/<id>-bec-defence` (this session) — all work lands on the
  branch currently attached to PR #1; pushing extends it. The maintainer
  merges; never merge or close the PR yourself.
- Commit style: short imperative subject; body explains *why* + any safety
  implications. Sign off with the honesty notes if limits changed.
- Tones: sober in docs; human-direct in stage copy. Never marketing.
- Language: English (docs). Citizen-facing strings: hi/te/en where present.

## 3. How to keep docs current (the "updated time to time" protocol)

After ANY substantive change:

1. Bump `Last updated` in the file you touched (and in this file only if
   rules changed).
2. Append a `CHANGELOG.md` entry (date · author/AI · what changed · why).
3. Synchronize the other docs that reference what you changed — search for
   the stale string before committing.
4. If you learn a new verified fact, add it to `CONTEXT.md §5` with status.
5. If reality contradicted a doc, fix the doc — do not explain the gap
   away in prose.

## 4. Definition of done (AI-authored change)

- [ ] Behavior implemented or doc written
- [ ] Tests green (or docs-only change clearly marked)
- [ ] `CHANGELOG.md` entry appended
- [ ] No unverified numbers introduced
- [ ] No safety rail relaxed
- [ ] `AI_HANDOFF.md` status line reflects reality
- [ ] Maintainer notified of judgment calls made

## 5. Current status (update me honestly)

| Area | State |
| --- | --- |
| EIGENSHIELD v2.1 FORTRESS | Built, tested, pushed (PR #1, open) |
| RAKSHA docs | **v0.9.0** — Phase 6–8 unified Infra integration, MessageGuard Phase 5 single-source, Phase 1 freeze, Phase 2 layout, Phase 3 contract spine and Phase 4 Citizen consolidation synced on 2026-11-26 |
| Combined-system plan | **Phase 6–8 unified implementation** — separate `apps/citizen` + `apps/infra`, shared `packages`, unified contracts, one MessageGuard scorer/corpus/eval, one detector registry, one deterministic safety brain and one read-only Infra console; VoiceGuard/MAYA hash-pinned; Phase 9/10 pending |
| raksha-code/ | **M1–M6 + Citizen phases SHIPPED** — Phase 4/5 no-AI subset: 196 deterministic pytest passed from repo root (171 from `raksha-code/`), 60 Node tests passed; 23 model-dependent Python files + 1 MAYA capture Node file skipped |
| Citizen app | **M3 SHIPPED, Phase 5 single-source** — one PWA + FastAPI service; MessageGuard measured on 538 hand-authored fixtures (real-world UNMEASURED); VoiceGuard/MAYA frozen, voice tab says "not integrated yet", no clone-detection claim |
| Sentinel app | **M2+M4+M5 SHIPPED** — shields + RAAVAN replay + campaign fusion + containment planner; executor stays dry-run |
| Evals & stage | **M6 tables reproducible** — `raksha/EVALS.md` + `raksha/MESSAGEGUARD_EVALS.md`; rehearsal/video/judges' script = human tasks (not doable in sandbox) |
| RAAVAN playbook | Shipped as a sandbox replay; full ten-technique stage choreography still a human task |
| Verification of [VERIFY] stats | OPEN — maintainer must pull PIB/CERT-In releases |
| Pilots | OPEN — no MoU yet |

## 6. Open decisions waiting on the maintainer

1. App names (Citizen/Sentinel are placeholders-in-use).
2. Hackathon date and team split (two apps build in parallel — need both rosters).
3. Whether RAKSHA lands inside this repo or a fresh one before public release.
4. Citizen app distribution for pilots (sideload APK vs PWA install prompt).
5. Whether to authorize Phase 6+ migrations; Phase 5 MessageGuard single-source is complete with no AI models run, but full legacy spine/sentinel/eval implementation moves still sit behind `packages/` facades.

## 7. Escalation triggers (stop working, ask now)

- Asked to point code at a live external target.
- Asked to suppress, minimize, or reword a safety regression.
- Asked to inflate measured results, or to publish unverified numbers.
- Ambiguity that changes the doctrine (delete a rail vs. add one).

## 8. House style for this repo's markdown

- Lead with what it is, then what it isn't, then how to use it.
- Tables for comparisons; plain sentences for rankings of risk.
- Every claim of fact carries a source tag or a verb like "is designed to".
- No emoji in formal docs; sparing in stage copy only.

## Phase 6–8 handoff

Do not reintroduce the legacy `spine.bus`, an AI Commander model import, a
second detector registry, a second ledger write path, or a console mutation
route. Start the unified app with `python -m apps.infra --port 8090` and open
`/app/console`. Deterministic gates:
[`../tools/check_phase678_integration.py`](../tools/check_phase678_integration.py)
and [`../tests/test_phase678_integration.py`](../tests/test_phase678_integration.py).
