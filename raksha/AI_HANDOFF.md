# AGENTS.md — Instructions for AI Agents working on RAKSHA

> **Audience:** any AI (this file is written for LLMs, autonomous agents and
> human engineers who think like them).
> **Last updated:** 2026-11-20 · **Living document** — keep it true.

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
| RAKSHA docs | v0.1.0 — initial set committed |
| raksha-code/ | **M1 SHIPPED** — spine + tests green (27/27), PR #1 |
| Citizen app | **M3 SHIPPED (demo-grade)** — PWA + FastAPI live on :8095; heuristic detectors labeled |
| Sentinel app | **M2+M4+M5 SHIPPED** — shields + RAAVAN replay + campaign fusion + containment planner live (67/67) |
| Evals & stage | **M6 IN PROGRESS** — measured table frozen in raksha/EVALS.md; rehearsal/video/judges' script = human tasks (not doable in sandbox) |
| RAAVAN playbook | NOT STARTED (spec'd in ARCHITECTURE §6) |
| Verification of [VERIFY] stats | OPEN — maintainer must pull PIB/CERT-In releases |
| Pilots | OPEN — no MoU yet |

## 6. Open decisions waiting on the maintainer

1. App names (Citizen/Sentinel are placeholders-in-use).
2. Hackathon date and team split (two apps build in parallel — need both rosters).
3. Whether RAKSHA lands inside this repo or a fresh one before public release.
4. Citizen app distribution for pilots (sideload APK vs PWA install prompt).

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
