# GOAL.md — the 10x contract for `control-anything`

> Per the spec rule: **§0 first.** Reflect the request, say what's weak in it, define the 10x so
> it can fail, and surface the decisions only Paul can make. Everything below §0 is downstream.

---

## §0 — Eval of the request

### The request, reflected back (≤6 lines)

Build a **meta-repo about control theory and its application across AI** — generative AI, agentic
AI, physical AI, robotics, world models, and domains I should name myself. Ship three organs: a
**knowledge base shaped as a graph** (contributors · seminal works · labs · open questions ·
applications · and more I name), **agentic tooling**, and a **community**. Borrow the organization
and operating principles that already work in `FDE-os`, `research-anything`, and the rest of the
`<X>-os` / `<X>-anything` family.

### What is weak in it, said plainly

1. **"Control theory and its application in AI" is a survey prompt, and surveys rot.** There are
   already hundreds of "awesome-control-theory" lists and review papers. A link farm is a
   commodity — it decays the week after it ships and nobody can tell when it has decayed. If this
   repo's output is *a curated list*, it has no reason to exist.
2. **The domain list is unbounded.** "generative AI, agentic AI, physical AI, robotics, world
   model, `<you-name-more>`" invites infinite scope. Without a stopping rule, the repo becomes a
   second Wikipedia with worse coverage.
3. **There is no signal loop in the request.** Nothing in it says how we'd know the repo is
   *right* rather than merely *large*. A knowledge base with no gate is a pile of claims, and the
   whole point of control theory is that an ungated loop drifts.
4. **"Community" is the part that silently fails.** Every meta-repo declares a community; almost
   none gets contributions. Declaring one is free; designing the contribution *gate* is the work.

### The 10X, defined so it can fail

The 10x is **not coverage. It is the gate.**

> **The claim this repo makes:** a control claim is worth exactly **the weakest assumption holding
> underneath it**. So every entry in the knowledge base carries a **guarantee level** (G0–G4) and
> an **assumption ledger**, and the repo *mechanically caps* the guarantee at what its assumptions
> actually discharge. "We used an MPC, therefore it is safe" is the single most common failure in
> applied control — and it is now a failing exit code here.

This turns a survey into an **instrument**. Concretely, the repo computes these numbers and
`make check` fails when they regress:

| # | Metric | Definition | Target within 30 days |
|---|---|---|---|
| 1 | **`capped`** | entries whose *claimed* guarantee exceeds their *effective* (assumption-capped) guarantee | ≥ 12 — the over-claims the gate actually caught |
| 2 | **`gate_coverage`** | fraction of knowledge-base claims that pass through `ControlClaimGate` | **1.00**, enforced by a graph reachability test (no claim may reach output bypassing the gate) |
| 3 | **`unverified_rate`** | fraction of citations not resolved against a primary source | ≤ 0.25, and the number is printed in the README, never hidden |
| 4 | **`orphans`** | knowledge-graph nodes with no edge to a loop organ | **0** |
| 5 | **`loopified`** | domains with a complete 6-organ `LoopCard` (reference · comparator · controller · actuator · plant · sensor) | ≥ 12 of 12 domains |

If `capped` is 0, the gate is decorative and **this repo has failed its thesis** — that is the
honest failure condition, written down in advance so it can actually trip.

### The stopping rule (answers weakness #2)

A domain earns a row in `data/domains.yml` only if it can produce **a complete `LoopCard`** — all
six organs named with real handles, plus latency, authority, and fallback. If you cannot say what
the sensor is, it is not a control problem and it does not belong here. **Twelve domains, closed
set**, listed in §2. Growth happens by *deepening* a domain, not by appending one.

### Decisions only Paul can make

| # | Decision | Why it is his | Default if he says nothing |
|---|---|---|---|
| D1 | ~~**Public or private?**~~ **DECIDED 2026-09-19: public.** Built public-safe from commit #1 — no confidential input, no client or employer named. | Venture positioning, not engineering. | ✅ Public. |
| D2 | ~~**Content flywheel or internal tool?**~~ **DECIDED 2026-09-19: content flywheel.** The gate's catches feed the agentic-portfolio article rail; long-form publishes canonically there first, then syndicates. | Flywheel choice — his half. | ✅ Content flywheel. |
| D3 | ~~**A 6th `<X>-anything` sibling, or a one-off?**~~ **DECIDED 2026-09-19: sibling.** Inherits `docs/REPO_PLAYBOOK.md`; §5 carries the seven lessons this build earned back to the family. | Portfolio shape. | ✅ Sibling. |

**Cofounder's call on the one thing that matters:** the highest-ROI move is **the gate, not the
corpus**. A hundred more citations change nothing; a gate that catches its first real over-claim
changes what the repo *is*. So the build order is gate → spine → corpus, not corpus → gate.

---

## §1 — The mental model (the 🧒 test)

**A thermostat is the whole idea.** You say what you want (72°F). A thermometer says what you have
(68°F). The gap between them is the *error*. The furnace does something about the gap. Then the
thermometer reads again — and that "reads again" is the entire subject. Without it you are
*hoping*; with it you are *controlling*.

Every system in this repo is that thermostat wearing a costume:

| The thermostat | The costume it wears here | The technical handle |
|---|---|---|
| the temperature you want | the prompt, the goal, the desired gait | **reference / setpoint** `r` |
| the gap between want and have | the loss, the reward, the tracking error | **error** `e = r − y` |
| the furnace's decision | the policy, the sampler, the MPC solve | **controller** `K` |
| the furnace itself | the actuator, the token emitted, the joint torque | **actuator** `u` |
| the room | the world, the user, the robot's body | **plant** `P` |
| the thermometer | the eval, the reward model, the encoder, the IMU | **sensor** `C` |

The 15-year-old leaves with: *"an AI agent is a thermostat whose room is the world, and most of
them are broken because nobody checked the thermometer."* The engineer leaves with: the six organs
are typed fields on `LoopCard` in `src/control_anything/core/models.py`, and a domain without all
six fails `make check`.

**Why control theory, and why now.** Control theory is the only mature branch of engineering whose
entire subject is *"this system acts, the world answers back, now what?"* — exactly the regime AI
just walked into. For fifty years AI systems were open-loop: input → output → done. An agent that
takes an action, observes the result, and acts again is a **closed loop**, and closed loops have a
hundred years of hard-won laws about when they converge, when they oscillate, and when they tear
themselves apart. We are rediscovering those laws expensively. This repo is the translation table.

---

## §2 — The twelve domains (closed set)

Each must produce a complete `LoopCard` or it is cut. Source of truth: `data/domains.yml`.

| # | Domain | The loop in one line |
|---|---|---|
| 1 | **Generative AI** | sampling guided toward a target distribution — guidance scale *is* a gain |
| 2 | **Agentic AI** | act → observe → act; the first genuinely closed loop in software AI |
| 3 | **Physical AI** | perception-to-torque on real hardware, where latency is not negotiable |
| 4 | **Robotics** | the classical plant: rigid bodies, contact, actuator limits |
| 5 | **World models** | a learned plant model — which is what MPC has always needed |
| 6 | **Alignment & AI safety** | human preference as the reference signal; oversight as a supervisory loop |
| 7 | **Autonomous driving** | the most-deployed safety-critical learned loop on Earth |
| 8 | **AI infrastructure** | serving, batching, autoscaling — textbook control wearing a GPU |
| 9 | **Medicine & biology** | closed-loop insulin, anesthesia, neuromodulation — where the plant is a person |
| 10 | **Power & energy** | grid frequency, inverters, datacenter cooling — the original hard real-time loop |
| 11 | **Aerospace** | where the discipline was forged and where certification means something |
| 12 | **Markets & mechanisms** | feedback among strategic agents; where control meets game theory |

---

## §3 — The three organs the request asked for

1. **Knowledge base (graph).** Typed nodes — `concept · person · work · lab · question ·
   application · domain · loop-organ` — in `data/*.yml`, assembled into a real graph with
   reachability invariants gated in CI. Not a list. A list cannot answer *"which assumption is
   load-bearing for this claim?"*; a graph can.
2. **Agentic tooling.** The flagship `/control-anything` skill plus verbs: **`loopify`** (map any
   system onto the six organs), **`gate`** (run `ControlClaimGate` over a claim), **`trace`**
   (walk the graph from a claim to its assumptions), **`brief`** (a window-dated answer).
3. **Community.** Contribution as a **gated protocol**, not an invitation: a new entry must carry
   its assumption ledger and pass `make check`. The gate is the community's shared language —
   the one thing that makes a stranger's PR reviewable in five minutes.

---

## §4 — Milestones (each with a runnable definition of done)

| M | Milestone | Definition of done (runnable) |
|---|---|---|
| M1 | Spine green at birth | `make check` exits 0 on an empty-but-valid spine |
| M2 | `LoopCard` + `ControlClaimGate` | `pytest` proves an over-claim is capped and a mutation of the gate fails the suite |
| M3 | Knowledge graph + reachability | `make graph` proves 0 orphans and 1.00 gate coverage |
| M4 | Corpus loaded, verification honest | `make check` prints `unverified_rate`; README drift-gated against it; every `verified: true` backed by a recorded primary-source answer (`data/resolutions.yml`) — ✅ 0.22 on 2026-09-24, target ≤ 0.25 |
| M5 | Flagship skill + verbs | `scripts/ca.py loopify\|gate\|trace\|brief` run offline and deterministically |
| M6 | Community protocol | `CONTRIBUTING.md` + a PR template that fails without an assumption ledger |
| M7 | Self-audit | `make ainative` ≥ 90, gated in CI |

---

## §5 — Honest edges (stated before anyone finds them)

- **The gate encodes a judgment, not a theorem.** The G0–G4 ladder and the capping rule are *our*
  design. They are defensible and mechanical, but they are not a result anyone proved.
- **Verification is bounded by what a web-research pass can confirm.** Every citation carries
  `VERIFIED` or `UNVERIFIED`, and `unverified_rate` is published rather than hidden.
- **The analogy/rigour split is the whole risk.** "RLHF is a control loop" is *sometimes* a real
  theorem (stochastic optimal control, mean-field control) and *sometimes* a vibe. Each bridge is
  tagged `rigorous` or `analogy`, and conflating them is the failure mode this repo most fears.
- **No live plant.** Nothing here runs a physical robot or a live model in `make check`. The gate
  is offline and deterministic by design; that is a feature, and also a limit on what it can prove.
