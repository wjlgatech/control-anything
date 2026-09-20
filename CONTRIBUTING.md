# Contributing

The community organ here is a **gated protocol**, not an invitation. Declaring a community
is free; designing the contribution gate is the work. This document is that gate.

## The one rule

> **Every claim carries its assumption ledger.**

You may add anything you like — a concept, a person, a paper, a deployed application, an
open question — but if you assert that some loop *achieves* something, you must say what
that achievement rests on, and whether each of those things is `discharged`, `monitored`,
`assumed`, or `violated`.

That is the shared language. It is what makes a stranger's pull request reviewable in five
minutes instead of an afternoon, because the reviewer's job becomes a specific question:
*is this assumption really monitored?* — not a vague one about whether the entry "seems right".

## Before you open a pull request

```bash
make check
```

Green, or it does not ship. The gate is offline and deterministic: no keys, no network, no
clock. If it passes on your machine it passes in CI.

## What a good contribution looks like

**The highest-value one, and the fastest:** find a claim in `data/claims.yml` whose
assumption ledger is *wrong*. Either direction moves a number:

- We marked something `assumed` that you can show is monitored in practice → name the check.
- We marked something `monitored` whose check does not actually fire, or has no fallback →
  downgrade it. A monitor with nothing behind it is not a monitor.

**Adding a claim.** Write what its authors (or the field's folklore) actually assert in
`claimed`, not what you think it deserves. The gate computes what it earns. If your claim
passes at the level asserted, say so plainly — the gate is a referee, not a wrecking ball,
and `speculative-decoding-exact` holding at G4 is as useful an entry as any refusal.

**Adding a work.** It needs a `year` and a resolvable `doi`, `arxiv`, `url` or `source`.
An uncheckable citation is worse than no citation, because it looks like evidence. If you
could not resolve it against a primary source, set `verified: false` — that is honest, and
the repo publishes the resulting rate rather than hiding it.

**Adding a person.** One `owns_concept`, pointing at a concept that exists. A person who
owns six things owns none; picking one is what keeps the graph navigable. If the concept
they own is finer-grained than our ontology, point at the concept it specialises and say so.

**Adding a domain.** Almost certainly don't. The twelve are a **closed set**, and the
stopping rule is in `GOAL.md §0`: a domain earns a row only if it can produce a complete
`LoopCard` — all six organs named with real handles, plus latency, authority and fallback.
Growth happens by *deepening* a domain, not by appending a thirteenth. If you genuinely
have a thirteenth, open an issue with the LoopCard filled in and argue for it there first.

**Tagging a bridge.** `rigorous` means there is a theorem — name it. `analogy` means it is
a useful framing. Mislabeling an analogy as rigorous is the one thing this repo most wants
to avoid, and the gate will refuse an `analogy` claiming G3 or above.

## What will get a pull request sent back

- A claim with no assumptions above G1.
- An assumption marked `monitored` or `discharged` with no `check` named. The loader
  rejects this outright, so you will see it before a reviewer does.
- A citation nobody can resolve.
- A metaphor typed as `rigorous`.
- A number written into prose without a gate asserting it. Any number in the README is
  generated from `data/` by `scripts/readme.py` — edit the spine, then run `make readme`.

## Style

Plain words first, then the precise term. Every explanation should pass two readers at
once: a bright fifteen-year-old who can restate the mental model afterwards, and an
engineer who can implement the section without asking "which one? in what shape? triggered
how?". If a sentence leads with jargon, rewrite it.

## Human-gated by design

Nothing here auto-posts, auto-merges, or auto-publishes. Network access lives outside
`make check` entirely. Merges are human, and always will be.
