# Architecture

## The shape, in one picture

```mermaid
flowchart TB
    subgraph SPINE["data/*.yml — the single source of truth"]
        D[domains]:::d
        C[concepts]:::d
        P[people]:::d
        W[works]:::d
        L[loops]:::d
        K[claims]:::d
    end

    subgraph CORE["src/control_anything/core — stdlib + pyyaml ONLY"]
        R[registry<br/><i>loads + validates FKs</i>]:::c
        M[models<br/><i>LoopCard · GuaranteeLevel<br/>Assumption · Claim</i>]:::c
        G[graph<br/><i>337 nodes / 863 edges</i>]:::c
        GATE[ControlClaimGate<br/><b>the thesis, executable</b>]:::g
    end

    subgraph GATES["make check — offline, deterministic, no keys"]
        T1[tools/check.py<br/>spine + foreign keys]:::t
        T2[tools/layers.py<br/>the layering law, by AST walk]:::t
        T3[ca.py graph --check<br/>0 orphans · coverage 1.0]:::t
        T4[ca.py gate --check<br/>≥12 over-claims caught]:::t
        T5[readme.py --check<br/>no drift from data/]:::t
        T6[ainative.py<br/>the repo still has its organs]:::t
    end

    SPINE --> R --> M
    M --> G
    M --> GATE
    R --> GATE
    GATE --> T4
    G --> T3
    SPINE --> T1
    CORE --> T2
    SPINE --> T5
    T1 & T2 & T3 & T4 & T5 & T6 --> OUT{{"exit 0 = green"}}:::o

    classDef d fill:#f0eee6,stroke:#b0aea5,color:#141413
    classDef c fill:#fff,stroke:#6a9bcc,color:#141413
    classDef g fill:#d97757,stroke:#d97757,color:#fff
    classDef t fill:#fff,stroke:#788c5d,color:#141413
    classDef o fill:#788c5d,stroke:#788c5d,color:#fff
```

## The gate, in one picture

This is the whole idea. A claim asserts a level; the gate computes what it earned.

```mermaid
flowchart LR
    CLAIM["claim<br/><i>claimed: G3 robust</i>"]:::in

    subgraph LEDGER["assumption ledger — combine by WORST"]
        A1["'solver returns in time'<br/><b>monitored</b> → ceiling G3"]:::ok
        A2["'model matches the robot'<br/><b>assumed</b> → ceiling G1"]:::bad
    end

    subgraph EVID["evidence — combine by BEST"]
        E1["hardware → ceiling G3"]:::ok
        E2["simulation → ceiling G2"]:::ok
    end

    MIN["effective = min(<br/>claimed, weakest assumption, best evidence)"]:::g
    OUT["🟡 <b>G3 → G1</b><br/>limited by assumption:model-match"]:::res

    CLAIM --> MIN
    LEDGER --> MIN
    EVID --> MIN
    MIN --> OUT

    classDef in fill:#f0eee6,stroke:#b0aea5,color:#141413
    classDef ok fill:#fff,stroke:#788c5d,color:#141413
    classDef bad fill:#fff,stroke:#d97757,color:#141413,stroke-width:2px
    classDef g fill:#d97757,stroke:#d97757,color:#fff
    classDef res fill:#f0eee6,stroke:#d97757,color:#141413,stroke-width:2px
```

**Why `min` on assumptions and `max` on evidence.** A chain is as strong as its weakest
link — one unchecked assumption undermines the whole guarantee, no matter how many good
ones surround it. Evidence is not a chain: having an analogy alongside a proof does not
weaken the proof. Inverting either is a mutation test in `tests/test_claim_gate.py`.

## The layering law

Core may import the standard library, `pyyaml`, and other core modules. Nothing else, ever.

`tools/layers.py` enforces it by walking the AST, so a **function-local** import counts
exactly like a top-level one — which is how dependencies actually creep in. A sibling repo's
equivalent check found two hidden edges on its first run that no top-of-file grep had shown.

Adding a core dependency means editing `CORE_THIRD_PARTY` in that file, on purpose. That
makes it a reviewed decision rather than an accident, because it widens what `make check`
needs on a bare machine — and "green on a bare machine" is what makes every generated
surface drift-checkable.

## Why the graph is stdlib

`networkx` was considered and rejected: it would put a third-party dependency in the core.
Roughly sixty lines of breadth-first search over adjacency dicts covers every query the
repo makes (`reachable`, `trace`, `degree`), and the invariants are all reachability
questions.

## Determinism

No clock, no network, no randomness anywhere under `make check`. `tests/conftest.py` strips
provider API keys so nothing can go live even by accident. Ties are broken by id — see
`Claim.weakest_assumption` — so verdicts are byte-identical across runs and machines.

That property is load-bearing, not cosmetic: it is precisely what lets the README's tables
be *generated* and then **drift-gated**. A flaky gate cannot check a document.
