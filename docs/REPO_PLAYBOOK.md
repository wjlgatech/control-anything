# REPO_PLAYBOOK — how an `-anything` / `-os` repo is built

> **Canonical source:** `Projects/_templates/REPO_PLAYBOOK.md` (seeded here by `new-project.sh`).
> This repo-local copy is an instance — edit the template, not this file, for cross-repo changes.
>
> The reusable pattern behind design-anything, research-anything, and this repo. Copied
> here on 2026-09-19 when control-anything was minted, with the lessons that repo earned
> appended as §5. The playbook is itself spec-as-data: the living checklist is
> `data/ainative.yml`, audited by `make ainative`.

## 0. The shape (what every repo has)

```
<name>/
├── GOAL.md              10x contract: verbatim intent → eval → the 10x move → milestone table
├── Makefile             `make check` = the offline, deterministic finish line
├── data/*.yml           the SINGLE SOURCE OF TRUTH (spec-as-data). Nothing hand-edited downstream.
├── docs/                ARCHITECTURE · SPEC · ROADMAP · LANDSCAPE · REPO_PLAYBOOK
├── src/<pkg>/           the OOP engine (typed models + single-responsibility services)
├── scripts/             thin CLIs over the engine (logic lives in src, never in the CLI)
├── tests/               pytest; every gate has an executable test
├── skills/              the flagship thin-router skill + generated use-<slug> satellites
├── research/            window-dated digests (30 days / months / years / 300 years)
├── llms.txt · README (with a drift-gated News block) · CHANGELOG · CONTRIBUTING · CLAUDE.md
└── .github/workflows/   check.yml (gate) + a weekly, human-gated sync
```

## 1. The non-negotiable disciplines (each is an `ainative.yml` principle)

- **spec-as-data** — curated knowledge lives in `data/*.yml`. Every published surface
  (README sections, skills, contracts) is GENERATED and **drift-gated** (`build --check`).
- **ready-is-a-gate** — the repo's domain has a definition of "done" encoded as a machine
  gate with exit codes (design = geometry; research = the claim-gate). A gate never vibes.
- **no-evidence-means-no** — an unmeasured/unreachable item is excluded, never a fake pass;
  a blocking gate cannot pass on unmeasured items.
- **maker-is-not-checker** — generators and gates are independent bodies, held together by
  tests. The thing that produces output never also blesses it.
- **satellites, never vendored** — a cited external repo is a pointer + a SHA-pinned digest
  + a generated thin skill. Freshness is *measured* (STALE flag), not promised.
- **compounding memory** — significant updates and lessons land in `data/` (news, tables,
  this playbook), not in chat. State lives outside the context window.
- **honest edges** — limitations are stated where users read them (README `## Honest edges`).
- **human-gated irreversible** — network sync opens a PR; merges and publishes stay human.
- **the repo audits itself** — `data/ainative.yml` + `scripts/ainative.py` score HOW the repo
  operates with in-repo evidence, gated in CI. A regression in operating-discipline fails
  the build just like a code regression.

## 2. The build loop (goal-10x)

Research (map, don't guess; read backbone + sibling repos) → Absorb (reflect intent in ≤6
lines) → Coach (≤2 forks) → **Drive to green** (verification is the only truth; drive the
*discovered* check) → Self-improve (bank the lesson into `data/`, not chat). The ROADMAP is a
machine-checkable milestone table; each milestone has a DoD you can run.

## 3. Lessons learned building research-anything (the upgrade)

These generalized beyond the repo that earned them — promote them into the playbook:

1. **The satellite pattern is domain-agnostic.** It began as design-anything's way to track
   3D-tooling repos; it works unchanged for a *research* meta-tool (deep-research engines,
   structure predictors, benchmarks). If your repo composes external repos, satellites are the
   answer — index + pinned digest + generated skill, never a fork.

2. **The gate's semantics are domain-specific; the gate *discipline* is universal.** Don't look
   for "the ready-gate" — build the gate that encodes YOUR domain's "verified." Here it's the
   **claim-gate**: a citation resolves + an evidence-type ceiling + an autonomy altitude gated
   by ground-truth cost + a mandatory anti-portfolio. Over-claiming is the one failure.

3. **Model the orchestration as a graph and gate reachability.** Domains/windows/modules + the
   gate form a graph; CI asserts *no orphan module* and *no module can reach output bypassing
   the gate*. This catches a whole class of wiring bugs a unit test wouldn't. (networkx.)

4. **Make the closed loop a real object.** `ClosedLoop`: generate → score vs an independent
   referee → refine, roll back regressions, report how it converged (F→A). The flagship runs
   its draft brief through the loop so an over-claim is impossible by construction.

5. **Benchmarks/evals are first-class modules with honest "not measured."** The eval spine is
   part of the product, not an afterthought; an absent benchmark reports `not measured` and the
   gate refuses to pass on only-unmeasured evidence.

6. **Keep the gate offline and deterministic; put all network in `sync` + a weekly workflow.**
   `make check` must run with no keys and give byte-identical output — otherwise CI is flaky and
   satellites can't be drift-checked.

7. **Digest a cited repo with a parallel sub-agent that pins the HEAD sha and flags unconfirmed
   facts.** Fan out one agent per repo; require the KNOWLEDGE.md to name the sha it was written
   against and to say "unconfirmed" rather than invent an install command or API signature.

8. **An evidence-type taxonomy is the antidote to "engagement is not evidence."** Tag every
   finding {observed · experimental-objective · survey-sampled · modeled-intent · engagement-proxy
   · llm-synthetic}; the weak ones cannot rank above ⚪ until they cross an adoption window.

9. **Don't chase a docstring-count metric.** `anyagent analyze` weights a `documentation`
   sub-score by docstrings-per-function; padding trivial getters/tests to lift it is the exact
   noise good practice forbids. Keep module/class/service docstrings meaningful and let the
   structural sub-scores (typing/testing/nesting/structure) carry the grade.

## 4. Minting the next repo

Start from `GOAL.md` (compile the intent), stand up `data/*.yml` + `make check` FIRST (green at
birth), then add the flagship skill, then satellites one repo at a time (candidate → digested →
integrated, each advance gated by on-disk evidence). Wire `ainative.yml` early so the repo holds
its own discipline from day one.


## 5. Lessons learned building control-anything (2026-09-19)

Appended per §3's rule — promote what generalizes beyond the repo that earned it.

1. **Build the gate BEFORE the corpus.** The temptation on a knowledge repo is to gather
   first and judge later; the gather never ends and the judging never starts. Build order
   here was gate → spine → corpus, and the first real catch (`mpc-humanoid-safe`, capped
   G3→G1 by an unchecked model-match assumption) arrived before the corpus was half full.
   A hundred more citations change nothing; the first catch changes what the repo *is*.

2. **Write the failure condition into GOAL.md in advance, as a number.** §0 states: *if
   `capped` is 0, the gate is decorative and this repo has failed its thesis.* That
   sentence is worth more than any amount of intent, because it can actually trip — and
   `make gate` exits non-zero on it. An improvement with no way to fail is taste.

3. **A closed set needs a MECHANICAL stopping rule, not a promise.** "Twelve domains" is
   enforced by "a domain without a complete LoopCard fails `make check`". Scope discipline
   that lives only in a README erodes in a week; scope discipline wired to an exit code does not.

4. **Type the difference between a theorem and a metaphor, and gate it.** In any
   cross-domain repo, half the material is rigorous and half is a useful framing, and
   nothing rots credibility faster than mixing them. One field (`bridge: rigorous|analogy`)
   plus one rule (an analogy cannot carry a strong guarantee) does the whole job.

5. **Measure your matching before trusting it.** Auto-matching 68 people to concepts by
   string similarity hit 25/68 — and the 43 misses were SILENT. Replaced with an explicit
   curated map in one reviewable place. When a heuristic's failures are invisible, count
   them before shipping it; curation you can read beats matching you cannot.

6. **Fan research out to bounded agents with a strict output contract, and make them mark
   VERIFIED vs UNVERIFIED per row.** Five parallel passes produced the corpus. The contract
   that mattered most: *never invent an arXiv id, DOI, or year; an empty cell beats a
   guessed one.* One pass independently corrected a lab attribution and caught three errors
   in a secondary source the user supplied — including a reversed author order — which is
   exactly the value a verification pass is supposed to add.

7. **Publish the unflattering number.** `unverified_rate` sits at 0.22 (it was 0.53 until verification became mechanical) and is printed in
   the README with an explanation, rather than being narrowed to the subset that looks
   good. A repo whose whole thesis is "state what your claim actually rests on" cannot
   launder its own metric.

## 6. The README contract (added 2026-09-19 — the axis this playbook was missing)

**The gap, named.** §0 above prescribes which FILES a repo has and which gates guard them.
Until today it said essentially nothing about what the README must CONTAIN. Those are two
different axes, and the playbook only had one — so a repo could be perfectly gated and still
open with a wall of prose that answers none of a stranger's questions.

The consequence was measurable the moment a gate existed to measure it. Scoring two repos
that were both built to this playbook, against a contract extracted from the better one:

| Repo | Score | Has | Lacks |
|---|---:|---|---|
| `anyagent` | **82/100** | mental model *with diagrams* · seams table · proof table · tested-with-command · docs index | **honest edges** · a compressed formula |
| `control-anything` | **55/100** | honest edges · formula · proof | **seams · docs index · provenance · a diagram in the README · the test command** |

Neither was complete, and each was missing what the other had. That is exactly the drift an
unwritten contract produces: two careful authors converging on different subsets.

**The contract.** Eleven sections, each answering a question a specific reader arrives with.
A section counts only when it carries the EVIDENCE its question demands — a mental model
without a diagram is prose; a "tested" section without a runnable command is a claim.

| Section | The reader's question | The evidence that makes it real |
|---|---|---|
| identity | What IS this? | a real sentence under the H1, not just a title |
| quickstart | How do I run it right now? | a fenced, runnable command block |
| **mentalmodel** | Can I picture how it works? | **a DIAGRAM** — Mermaid or a committed SVG |
| formula | What is the idea in one line? | a compressed identity or a pull-quote |
| **seams** | What can I swap? | a table naming what swaps and what bodies ship |
| proof | Has this touched reality? | a table of real cases |
| tested | How do I know it works? | the actual command, and the count it produces |
| **docsindex** | Where is everything else? | a table linking each doc to what is in it |
| honest | What does it NOT do? | actual stated limits |
| provenance | What is it made of / carrying? | dependencies, and what it deliberately does not carry |
| license | May I use it? | — |

**The ratchet.** `tools/readme_contract.py` scores it, `data/readme-floor.json` records the
floor, and `make check` runs it. The floor only rises. The gate takes an optional path, so
you can point it at any repo — which is how the contract was calibrated, and how you check
a sibling before copying from it.

**Two things this earned on its first run, both worth keeping:**

1. **The gate had a bug that made three checks unpassable.** `\S{40,}` matches forty
   *consecutive non-space* characters — a URL, never a sentence. Both repos "failed"
   identity for a reason that was the checker's fault. Caught by running the gate against
   the repo it was extracted FROM and asking why the source of the pattern scored badly on
   its own pattern. **Calibrate a new gate against a known-good artifact**; if the exemplar
   fails, suspect the gate first.
2. **A section can be present and still not count.** Every heading-only match is a place
   where a reader's question was acknowledged and not answered. That distinction is the
   whole value; checking headings alone would let a table of contents satisfy the contract.
