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

### Decisions worth not re-litigating

- **The gate, not the corpus, is the product.** Build order was gate → spine → corpus. A
  hundred more citations change nothing; the first real catch changes everything.
- **`bridge: rigorous | analogy` on every control-to-AI mapping.** Diffusion sampling *is*
  stochastic optimal control (a theorem). "Context is a saturating actuator" is a framing.
  An `analogy` claiming G3+ is refused. Conflating the two was judged the single largest
  risk to the repo's credibility.
- **Twelve domains, closed set.** Unbounded scope was the clearest weakness in the original
  request. The LoopCard requirement is the mechanical stopping rule.
- **`unverified_rate` is published, not hidden** (currently 0.53). Roughly half the claim
  corpus is ambient folklore recorded as folklore. Printing the corpus-wide number rather
  than the flattering `works.yml` subset.
- **Two contested death dates marked `verified: false`** rather than asserted. A secondary
  source reported them; no primary source confirmed. These are real people.

### Investigated / Rejected

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
