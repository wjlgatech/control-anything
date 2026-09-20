#!/usr/bin/env python3
"""``ca`` — the control-anything command line.

Thin CLI over the engine. All logic lives in ``src/control_anything``; this file only
parses arguments and prints. Offline and deterministic: no clock, no network, no keys.

Verbs:
  loopify  map a system onto the six organs (or show a stored LoopCard)
  gate     judge claims against their assumptions
  trace    walk the knowledge graph from a claim to what it rests on
  graph    knowledge-graph invariants
  loops    LoopCard completeness
  stats    the GOAL.md metrics
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from control_anything.core.claim_gate import ControlClaimGate  # noqa: E402
from control_anything.core.graph import build_graph  # noqa: E402
from control_anything.core.models import Organ, SpineError  # noqa: E402
from control_anything.core.registry import Registry  # noqa: E402


def _load():
    try:
        return Registry(ROOT).load()
    except SpineError as exc:
        print(f"✗ spine error: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc


# --------------------------------------------------------------------------------------
# loopify
# --------------------------------------------------------------------------------------


def cmd_loopify(args: argparse.Namespace) -> int:
    """Show a stored LoopCard, or print the blank template for a new system."""
    spine = _load()

    if args.system is None:
        print("The six organs every feedback loop has:\n")
        for organ in Organ:
            print(f"  {organ.value:<12} {organ.plain}")
        print(
            "\nPlus the three fields people forget, and where real systems fail:\n"
            "  latency      every loop has delay; delay is what turns a stable controller unstable\n"
            "  authority    what the controller is ALLOWED to do\n"
            "  fallback     what happens when the loop fails ('nothing' is a valid, damning answer)\n"
        )
        print(f"Stored cards: {', '.join(sorted(l.id for l in spine.loops))}")
        return 0

    matches = [l for l in spine.loops if args.system in (l.id, l.system)]
    if not matches:
        near = [l.id for l in spine.loops if args.system.lower() in l.id.lower()]
        print(f"✗ no loop card {args.system!r}", file=sys.stderr)
        if near:
            print(f"  did you mean: {near}", file=sys.stderr)
        return 1

    for loop in matches:
        print(f"\n── {loop.system}")
        print(f"   domain: {loop.domain}   id: {loop.id}\n")
        for organ in Organ:
            print(f"  {organ.value:<12} {loop.organ(organ)}")
        print()
        for field in ("latency", "authority", "fallback"):
            value = getattr(loop, field)
            mark = " " if value else "✗"
            print(f" {mark}{field:<12} {value or '— MISSING —'}")
        if loop.notes:
            print(f"\n  note: {loop.notes.strip()}")
        if loop.gaps:
            print(f"\n  incomplete — missing: {loop.gaps}")
    return 0


# --------------------------------------------------------------------------------------
# gate
# --------------------------------------------------------------------------------------


def cmd_gate(args: argparse.Namespace) -> int:
    """Judge the claim corpus. With --check, fail if the gate never catches anything."""
    spine = _load()
    gate = ControlClaimGate()

    claims = spine.claims
    if args.claim:
        claims = tuple(c for c in claims if c.id == args.claim)
        if not claims:
            print(f"✗ no claim {args.claim!r}", file=sys.stderr)
            return 1

    verdicts = gate.judge_all(claims)
    stats = gate.stats(claims)

    if args.json:
        print(json.dumps(
            {
                "stats": stats.as_dict(),
                "verdicts": [
                    {
                        "id": v.claim_id,
                        "claimed": v.claimed.code,
                        "effective": v.effective.code,
                        "outcome": v.outcome,
                        "limiting": v.limiting,
                        "reasons": list(v.reasons),
                    }
                    for v in verdicts
                ],
            },
            indent=2,
        ))
        return 0

    for verdict in verdicts:
        if args.verbose or args.claim:
            print(verdict.explain())
            print()
        else:
            print(verdict.headline)

    print(
        f"\n  {stats.total} claims · ✅ {stats.passed} held · 🟡 {stats.capped} capped · "
        f"⛔ {stats.refused} refused · ⚪ {stats.unproven} unproven · "
        f"unverified_rate {stats.unverified_rate}"
    )

    if args.check:
        # The thesis test, stated in GOAL.md: if the gate never catches an over-claim it
        # is decorative, and the repo has failed its own premise. An honest failure
        # condition, written in advance so it can actually trip.
        caught = stats.capped + stats.refused
        if caught < args.min_caught:
            print(
                f"\n✗ gate: caught only {caught} over-claim(s), need ≥ {args.min_caught}. "
                "A gate that never fires is decorative — see GOAL.md §0.",
                file=sys.stderr,
            )
            return 1
        print(f"✓ gate: {caught} over-claim(s) caught (≥ {args.min_caught} required)")
    return 0


# --------------------------------------------------------------------------------------
# trace
# --------------------------------------------------------------------------------------


def cmd_trace(args: argparse.Namespace) -> int:
    """Walk from a node to the things it rests on."""
    spine = _load()
    graph = build_graph(spine)

    start = args.node if ":" in args.node else f"claim:{args.node}"
    if graph.node(start) is None:
        print(f"✗ no node {start!r}", file=sys.stderr)
        candidates = [n.id for n in graph.walk() if args.node.lower() in n.id.lower()][:8]
        if candidates:
            print(f"  did you mean: {candidates}", file=sys.stderr)
        return 1

    node = graph.node(start)
    print(f"\n── {node.kind}: {node.label}\n")

    for kind in (args.to,) if args.to else ("concept", "domain", "work", "organ"):
        paths = graph.trace(start, kind)
        if not paths:
            continue
        print(f"  → {kind}:")
        for path in paths[: args.limit]:
            print(f"      {' → '.join(path)}")
        if len(paths) > args.limit:
            print(f"      … and {len(paths) - args.limit} more")
        print()
    return 0


# --------------------------------------------------------------------------------------
# graph / loops / stats
# --------------------------------------------------------------------------------------


def cmd_graph(args: argparse.Namespace) -> int:
    spine = _load()
    report = build_graph(spine).check()

    if args.json:
        print(json.dumps({
            "nodes": report.nodes,
            "edges": report.edges,
            "gate_coverage": report.gate_coverage,
            "orphans": list(report.orphans),
            "unmapped_concepts": list(report.unmapped_concepts),
            "ungated_claims": list(report.ungated_claims),
            "kinds": report.kind_counts,
        }, indent=2))
        return 0

    print(f"  {report.nodes} nodes · {report.edges} edges")
    for kind, count in report.kind_counts.items():
        print(f"    {kind:<12} {count}")
    print(f"  gate_coverage {report.gate_coverage}")

    if not report.ok:
        print("✗ graph invariants violated:", file=sys.stderr)
        for failure in report.failures():
            print(f"    - {failure}", file=sys.stderr)
        return 1
    print("✓ graph: 0 orphans · every concept maps to an organ · every claim reaches the gate")
    return 0


def cmd_loops(args: argparse.Namespace) -> int:
    spine = _load()
    incomplete = [l for l in spine.loops if not l.is_complete]
    domains_without = spine.domain_ids() - {l.domain for l in spine.loops}

    for loop in spine.loops:
        mark = "✓" if loop.is_complete else "✗"
        gaps = f"  missing: {loop.gaps}" if loop.gaps else ""
        print(f"  {mark} {loop.id:<24} {loop.domain:<14}{gaps}")

    if args.check and (incomplete or domains_without):
        print("✗ loops:", file=sys.stderr)
        if incomplete:
            print(f"    - {len(incomplete)} incomplete card(s)", file=sys.stderr)
        if domains_without:
            print(f"    - domains with no card: {sorted(domains_without)}", file=sys.stderr)
        return 1
    print(f"✓ loops: {len(spine.loops)} complete card(s) covering {len(spine.domains)} domains")
    return 0


def cmd_stats(args: argparse.Namespace) -> int:
    """The GOAL.md metrics, in one place."""
    spine = _load()
    gate = ControlClaimGate()
    stats = gate.stats(spine.claims)
    report = build_graph(spine).check()
    verdicts = gate.judge_all(spine.claims)

    metrics = {
        "capped": stats.capped + stats.refused,
        "gate_coverage": report.gate_coverage,
        "unverified_rate": stats.unverified_rate,
        "orphans": len(report.orphans),
        "loopified": sum(1 for l in spine.loops if l.is_complete),
        "domains": len(spine.domains),
        "concepts": len(spine.concepts),
        "people": len(spine.people),
        "works": len(spine.works),
        "labs": len(spine.labs),
        "questions": len(spine.questions),
        "applications": len(spine.applications),
        "claims": stats.total,
        "nodes": report.nodes,
        "edges": report.edges,
    }

    if args.json:
        print(json.dumps(metrics, indent=2))
        return 0

    print("\n  GOAL.md metrics\n")
    print(f"    capped           {metrics['capped']:>6}   over-claims the gate caught (target ≥ 12)")
    print(f"    gate_coverage    {metrics['gate_coverage']:>6}   claims reaching the gate (target 1.0)")
    print(f"    unverified_rate  {metrics['unverified_rate']:>6}   citations unresolved (target ≤ 0.25)")
    print(f"    orphans          {metrics['orphans']:>6}   unreachable nodes (target 0)")
    print(f"    loopified        {metrics['loopified']:>6}/{metrics['domains']}   domains with a complete LoopCard")
    print("\n  corpus\n")
    for key in ("concepts", "people", "works", "labs", "questions", "applications", "claims"):
        print(f"    {key:<16} {metrics[key]:>6}")
    print(f"    {'graph':<16} {metrics['nodes']:>6} nodes, {metrics['edges']} edges")

    worst = [v for v in verdicts if v.was_capped][:5]
    if worst:
        print("\n  the gate's most recent catches\n")
        for verdict in worst:
            print(f"    {verdict.headline}")
    print()
    return 0


# --------------------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="ca",
        description="control-anything — control theory as an instrument for judging AI systems",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("loopify", help="map a system onto the six organs")
    p.add_argument("system", nargs="?", help="loop id or system name; omit for the template")
    p.set_defaults(func=cmd_loopify)

    p = sub.add_parser("gate", help="judge claims against their assumptions")
    p.add_argument("claim", nargs="?", help="one claim id; omit for the whole corpus")
    p.add_argument("--check", action="store_true", help="fail if the gate catches too little")
    p.add_argument("--min-caught", type=int, default=12, help="minimum over-claims caught")
    p.add_argument("-v", "--verbose", action="store_true", help="show every reason")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_gate)

    p = sub.add_parser("trace", help="walk the graph from a claim to what it rests on")
    p.add_argument("node", help="claim id, or a namespaced node id like concept:mpc")
    p.add_argument("--to", help="target node kind")
    p.add_argument("--limit", type=int, default=6)
    p.set_defaults(func=cmd_trace)

    p = sub.add_parser("graph", help="knowledge-graph invariants")
    p.add_argument("--check", action="store_true")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_graph)

    p = sub.add_parser("loops", help="LoopCard completeness")
    p.add_argument("--check", action="store_true")
    p.set_defaults(func=cmd_loops)

    p = sub.add_parser("stats", help="the GOAL.md metrics")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_stats)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
