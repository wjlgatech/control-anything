# CLAUDE.md — control-anything

## What this is
Control theory as an **instrument for judging AI systems**, not a reading list about it.
The thesis: *a control claim is worth exactly the weakest assumption holding it up.* Every
entry carries a guarantee level (G0–G4) and an assumption ledger; `ControlClaimGate`
mechanically caps the guarantee at what those assumptions discharge.

## Session start
1. Read this file, then `GOAL.md` (the 10x contract — §0 evaluates the request itself).
2. Run `make check`. Spine · layers · graph · gate · readme · ainative · pytest must all
   pass (exit 0) before any change lands. It is offline and deterministic — no keys, no
   network, no clock. `tests/conftest.py` strips provider keys so nothing can go live.
3. The engine is `src/control_anything/core/` — `models` · `claim_gate` · `graph` ·
   `registry`. Thin CLIs in `scripts/`, gates in `tools/`, tests in `tests/`.

## The one rule
`data/*.yml` is the single source of truth. README tables are **generated** from it and
drift-gated by `scripts/readme.py --check`. Edit the spine, then `make readme`.
Never hand-edit a generated block; never type a number into prose that no gate asserts.

## The layering law (enforced by `tools/layers.py`)
Core imports only the standard library, `pyyaml`, and other core modules — **function-local
imports count**, because it walks the AST. Core never reaches into `addons`. To add a core
dependency you must edit `CORE_THIRD_PARTY` in `tools/layers.py` on purpose.

## Invariants you must not break
- **Six organs are a closed set.** `Organ` in `models.py`. A LoopCard missing one is rejected.
- **A `monitored` or `discharged` assumption must name its `check`.** An unnamed check is a wish.
- **Assumptions combine by WORST (`min`), evidence by BEST (`max`).** Inverting either
  guts the gate. Both are covered by mutation tests in `tests/test_claim_gate.py`.
- **An `analogy` bridge cannot claim G3 or above.** Refused outright.
- **Gate coverage must stay 1.0** and orphan nodes must stay 0.
- **The gate must keep catching ≥ 12 over-claims.** `make gate` fails otherwise — a gate
  that never fires is decorative (GOAL.md §0).

## Domains are closed
Twelve, and the stopping rule is mechanical: a domain with no complete LoopCard fails
`tools/check.py`. Growth is by *deepening*, never by appending a thirteenth. If you think
you have one, it needs a full LoopCard first — six organs plus latency, authority, fallback.

## Honesty rules specific to this repo
- `verified: false` is the correct answer when a primary source was not resolved. The
  repo publishes `unverified_rate` (currently 0.53) rather than narrowing to a flattering
  subset. Never flip a row to `verified: true` without actually resolving it.
- Never assert a death date, affiliation, or author order from a secondary source. Two
  rows in `people.yml` carry contested death dates marked unverified for exactly this reason.
- `bridge: rigorous` means a theorem exists and you can name it. Everything else is `analogy`.

## Sibling repos
Same operating system, different domains: `research-anything`, `FDE-os`, and the
`<X>-os` / `<X>-anything` family. Shared pattern: `docs/REPO_PLAYBOOK.md` (§5 holds the
lessons this repo earned).
