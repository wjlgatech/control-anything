# Changelog

All notable changes to this project are documented here, in
[Keep a Changelog](https://keepachangelog.com/) format.

## [Unreleased]

### Added

- **The repo.** `control-anything` — control theory as an instrument for judging AI
  systems, rather than a reading list about it. Why: a curated list of control-theory
  links is a commodity that rots silently; a gate that catches a real over-claim changes
  what the artefact *is*.
- **`ControlClaimGate`** (`src/control_anything/core/claim_gate.py`) — the thesis made
  executable: `effective = min(claimed, weakest-assumption-ceiling, best-evidence-ceiling)`.
  An `assumed` assumption ceilings a claim at G1, a `monitored` one at G3, a `violated` one
  refuses outright. Catches 30 over-claims across the 32-claim corpus.
- **`LoopCard`** (`models.py`) — the six organs (reference · comparator · controller ·
  actuator · plant · sensor) plus latency, authority and fallback. Twelve complete cards,
  one per domain. A domain without a complete card fails `make check` — that is the
  stopping rule that keeps scope closed.
- **Knowledge graph** (`graph.py`) — 337 nodes / 863 edges over typed node kinds, with
  three CI-gated invariants: no orphans, gate coverage 1.0, every concept maps to an organ.
  Pure stdlib BFS; networkx deliberately not used so `make check` runs on a bare machine.
- **The spine** (`data/*.yml`) — 12 domains, 56 concepts, 68 people, 86 works, 16 labs,
  34 applications, 27 open questions, 32 claims. Single source of truth; README tables are
  generated from it and drift-gated by `scripts/readme.py --check`.
- **`scripts/ca.py`** — CLI verbs `loopify`, `gate`, `trace`, `graph`, `loops`, `stats`.
- **Gates**: `tools/check.py` (spine + foreign keys), `tools/layers.py` (the layering law,
  enforced by AST walk so function-local imports count), `scripts/ainative.py` (self-audit
  of operating discipline, gated at 90).
- **54 tests**, including four **mutation tests** that break the gate in different ways and
  assert the suite notices. A gate that cannot fail proves nothing.

### Added — the README contract (2026-09-19)

- **`tools/readme_contract.py`** — eleven sections, each answering a question a specific
  reader arrives with, and each requiring the EVIDENCE its question demands. A mental model
  without a diagram is prose; a "tested" section without a runnable command is a claim.
  Wired into `make check`; floor in `data/readme-floor.json`; floor only rises.
- **`docs/REPO_PLAYBOOK.md` §6** — the axis the playbook was missing. §0 prescribed which
  FILES a repo has and which gates guard them, and said essentially nothing about what the
  README must CONTAIN.
- **README 55 → 100.** Added a Mermaid diagram of the six-organ loop (the README had no
  diagram at all), a seams table, a tested-to-the-gate section with the real command, a docs
  index, and a provenance section.
- **`tests/test_readme_contract.py`** — ten tests including four mutation tests that delete a
  section and assert the score drops, plus one proving a bare table of contents cannot pass.

### Investigated / Measured (2026-09-19)

- **The gate's first run found a bug in the gate.** Three checks used `\S{40,}` — forty
  *consecutive non-space* characters, which matches a URL and never a sentence. Both repos
  "failed" `identity` for a reason that was the checker's fault. Found by running the gate
  against the repo the contract was extracted FROM and asking why the exemplar scored badly
  on its own pattern. **Calibrate a new gate against a known-good artifact; if the exemplar
  fails, suspect the gate.**
- **Measured, both repos, same gate:** `anyagent` 82/100 — has mental-model-with-diagrams,
  seams, proof, tested, docs index; lacks **honest edges** entirely. `control-anything`
  55/100 — had honest edges and a formula; lacked seams, docs index, provenance, a diagram,
  and the test command. Neither was complete, and each was missing what the other had. That
  is exactly the drift an unwritten contract produces.

### Added — CI restored (2026-09-24)

- **`.github/workflows/check.yml`** — `make check` on every push and PR, closing GOAL.md M7
  ("gated in CI"). Held back since 2026-09-19 only because the gh token lacked `workflow` scope.

### Added — verification is earned, not typed (2026-09-24)

- **`data/resolutions.yml` + `make resolve`** (`scripts/resolve.py`) — the one networked
  target. Asks each source's primary service (arXiv via its DataCite DOI, doi.org, Open
  Library, the page itself) and records the title it returned. 117 handles on record.
  Why: `verified: true` was a flag a human typed — the exact unearned guarantee the gate
  exists to catch in everyone else's claims.
- **`core/citations.py` + a new clause in `tools/check.py`** — offline: every verified claim
  *and* work must name a handle (arXiv / DOI / URL / ISBN) and every handle must be on record.
  First run caught `context-engineering-controls-agents` verified with prose for a source,
  and Wiener's *Cybernetics* verified against a URL that 403s to machines (now its ISBN).
- **Ten claims resolved to primary sources** after reading each abstract against the claim
  (NEJM closed-loop insulin trial, NTSB ASR-19-01, GR00T N1, Hi Robot, VLM-RM, DreamGen,
  Reluplex + VNN-COMP, Kundur, the LULD evaluation, MIRAGE + LAP). `unverified_rate`
  0.53 → **0.22**, under the GOAL.md target of 0.25. The seven left are six folklore claims
  with no primary by design, plus DO-178C (paywalled).
- **`ca brief <domain>`** (`make brief D=…`) — the fourth verb GOAL.md §3 promised: one
  domain on one page — loop, claims judged, the weakest assumption under each, open
  questions — dated by the newest resolution, never the clock, so it stays deterministic.
- **A prose-number gate** (`test_prose_unverified_rate_matches_the_gate`) — the old 0.53 sat
  un-gated in five docs after the number moved. Now any stale current figure fails `pytest`.
  The article at agentic-portfolio was updated in all five languages in a paired PR.

### Decisions worth not re-litigating

- **The gate, not the corpus, is the product.** Build order was gate → spine → corpus. A
  hundred more citations change nothing; the first real catch changes everything.
- **`bridge: rigorous | analogy` on every control-to-AI mapping.** Diffusion sampling *is*
  stochastic optimal control (a theorem). "Context is a saturating actuator" is a framing.
  An `analogy` claiming G3+ is refused. Conflating the two was judged the single largest
  risk to the repo's credibility.
- **Twelve domains, closed set.** Unbounded scope was the clearest weakness in the original
  request. The LoopCard requirement is the mechanical stopping rule.
- **`unverified_rate` is published, not hidden** (0.53 at launch, 0.22 since resolution became mechanical). Roughly half the claim
  corpus is ambient folklore recorded as folklore. Printing the corpus-wide number rather
  than the flattering `works.yml` subset.
- **Two contested death dates marked `verified: false`** rather than asserted. A secondary
  source reported them; no primary source confirmed. These are real people.

### Investigated / Rejected

- **arXiv export API as the primary resolver** — rejected 2026-09-24: after the first call it
  answered 429 for every subsequent id even with 3→24 s backoff (10/11 failed in one probe).
  The DataCite DOI `10.48550/arXiv.<id>` via doi.org resolved all of them first try.
- **Hitting the 0.25 target by pairing folklore claims with adjacent papers** — rejected: a
  source must state the claim, not sit near it. Open X-Embodiment and π0 were resolved and
  NOT used for `vla-zero-shot-embodiment`, because neither claims zero-shot transfer to an
  unseen body; MIRAGE and LAP do.

- **networkx for the graph.** Rejected: it would put a third-party dependency in the core
  and break "runs on a bare machine". A sibling repo hit exactly this and had to back it
  out. ~60 lines of stdlib BFS covers every query the repo makes.
- **Fuzzy string-matching `person.owns` to concept ids.** Rejected after measuring: it
  matched only 25 of 68, and the failures were silent. Replaced with an explicit curated
  map in one reviewable place — this is a curation decision, not a string-matching problem.
- **A 13th–20th domain** (quantum control, chemical process safety, air-traffic
  management). All genuinely qualify. Deferred on purpose: the stopping rule is worth more
  than the coverage, and it is named in `README.md § Honest edges`.
- **Letting `make ainative` score quality rather than presence.** Rejected as
  unmeasurable by a file check; the limitation is stated in Honest edges instead of faked.
