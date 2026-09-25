---
name: control-anything
description: >-
  Judge whether an AI system's safety/reliability claim actually holds, by mapping it onto
  the six organs of a feedback loop and capping its guarantee at what its assumptions
  discharge. Use when someone claims a system "is safe", "is stable", "is aligned", "is
  reliable", or "handles X" — especially for agents, robot policies, RLHF pipelines,
  autoscalers, or anything with a loop. Triggers on 'is this safe', 'will this be stable',
  'control theory', 'guarantee', 'what could go wrong with this loop', 'review this
  architecture for failure modes'. NOT for tuning an actual PID controller.
---

# control-anything — judge the claim, not the vibe

## The one rule

> **A control claim is worth exactly the weakest assumption holding it up.**

Your job is not to say whether a system is good. It is to compute what its claim has
*earned*, and name what held it back.

## Step 1 — Map it onto the six organs

Every feedback loop has exactly these, whatever costume it wears. Fill all six with **real
handles**, not categories:

| Organ | The question | Example (LLM agent) |
|---|---|---|
| reference | What does it want? | the user's goal, stated once |
| comparator | How does it see the gap? | *often nothing at all* |
| controller | What decides? | the next-token policy |
| actuator | What acts? | the emitted tool call |
| plant | What is acted on? | filesystem, network, the user |
| sensor | What reports back? | tool return values |

Then the three fields people skip, which is where real systems fail:

- **latency** — delay is what turns a stable controller unstable.
- **authority** — what the controller is *allowed* to do. Unbounded authority from a single
  unverified signal is the 737 MAX structure.
- **fallback** — what happens when it fails. *"Nothing"* is a valid and damning answer.

**If you cannot name the sensor, it is not a control problem — it is a hope.** Say so.

## Step 2 — Write the assumption ledger

List what must be true for the claim to mean anything. For each, assign a status:

| Status | Meaning | Ceiling |
|---|---|---|
| `discharged` | proven, or interlocked in hardware | G4 |
| `monitored` | a runtime check fires **and something happens when it does** | G3 |
| `assumed` | believed, unverified, unwatched | **G1** |
| `violated` | known false | G0 — refused |

**A `monitored` or `discharged` assumption must name its check.** An unnamed check is a wish.

## Step 3 — Compute the cap

```
effective = min(claimed, weakest-assumption-ceiling, best-evidence-ceiling)
```

Assumptions combine by **worst** (one weak link caps everything). Evidence combines by
**best** (a proof is not weakened by also having an analogy).

Guarantee ladder: **G0** it worked once · **G1** we measured it · **G2** we bounded it with
a confidence level · **G3** it holds against any disturbance we listed · **G4** a machine
checked the proof.

Report it like this:

```
🟡 claimed G3 -> effective G1 (we measured it), limited by assumption:model-match
    - 'model-match' is assumed (the dynamics model matches the real robot) -> caps at G1
```

## Step 4 — Check for the five archetypal failures

These recur across aerospace, power, medicine, finance and computing. Ask each one:

1. **Sensed the command, not the plant.** Does it confirm the *effect*, or just that the
   instruction was sent? ("I called the API" ≠ "it worked".)
2. **Common-mode "redundancy".** Are the two copies identical? N copies of the same bug is N=1.
3. **Positive feedback.** Does the output become the next input? Does it read its own
   earlier mistakes? Is throughput governed by a number it itself inflates?
4. **Integrator with no termination.** What tells the loop it is finished? Is there a
   budget, a ceiling, a kill switch *above* the agent?
5. **Guard removed or never validated.** Does the checker check the thing that can actually
   kill you? A validator with a hole manufactures confidence.

## Step 5 — Separate theorem from metaphor

Tag the control mapping:

- **`rigorous`** — there is a theorem; name it. (Diffusion sampling *is* stochastic optimal
  control. Speculative decoding *has* an exactness proof.)
- **`analogy`** — a useful framing, nothing more. ("Context is a saturating actuator.")

**An analogy can never carry a G3+ guarantee.** Say so plainly when someone reaches for one.

## The move that fixes most of what you'll find

Most systems cannot make their learned part trustworthy. They don't have to. The pattern
that works in deployed practice — datacenter cooling, flight control, runtime assurance —
is **Simplex**: let the clever unverified controller run, but put a *proven-safe baseline*
behind a monitor that can take over, and let a human exit at any time. The guarantee lives
in the constraint layer, not in the policy. Recommend this before recommending a better model.

## If the repo is available

```bash
python3 scripts/ca.py loopify <system>   # the six organs for a stored system
python3 scripts/ca.py gate <claim-id>    # full verdict with reasons
python3 scripts/ca.py trace <claim-id>   # what the claim rests on
python3 scripts/ca.py brief <domain>     # one domain on one page, dated by its data
python3 scripts/ca.py stats              # corpus-wide metrics
```

Otherwise run the five steps by hand — they need no tooling.
