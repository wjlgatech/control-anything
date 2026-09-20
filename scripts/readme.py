#!/usr/bin/env python3
"""Generate the README's data-driven blocks, and gate them against drift.

Any number in prose is a claim; the scorer is the measurement; a test must assert they
agree. So the README's tables and metrics are GENERATED from ``data/`` between marker
comments, and ``--check`` fails the build when the file on disk disagrees.

Usage:
    python3 scripts/readme.py           # rewrite the generated blocks
    python3 scripts/readme.py --check   # fail if they have drifted
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from control_anything.core.claim_gate import ControlClaimGate  # noqa: E402
from control_anything.core.graph import build_graph  # noqa: E402
from control_anything.core.registry import Registry  # noqa: E402

README = ROOT / "README.md"


def _block(name: str, body: str) -> tuple[str, str]:
    return f"<!-- BEGIN:{name} -->", f"<!-- END:{name} -->"


def render_metrics(spine, gate, report) -> str:
    stats = gate.stats(spine.claims)
    caught = stats.capped + stats.refused
    loopified = sum(1 for l in spine.loops if l.is_complete)
    return "\n".join([
        "| Metric | Value | What it means |",
        "|---|---:|---|",
        f"| **over-claims caught** | **{caught}** | claims asserting more than their assumptions earn |",
        f"| claims judged | {stats.total} | every one passes through the gate |",
        f"| held | {stats.passed} | the guarantee stood as claimed |",
        f"| capped | {stats.capped} | downgraded to what the assumptions support |",
        f"| refused | {stats.refused} | a violated assumption, or a metaphor claiming a theorem |",
        f"| gate coverage | {report.gate_coverage} | fraction of claims that reach the gate (must be 1.0) |",
        f"| unverified rate | {stats.unverified_rate} | citations not resolved to a primary source |",
        f"| orphan nodes | {len(report.orphans)} | graph nodes nothing can reach (must be 0) |",
        f"| complete LoopCards | {loopified}/{len(spine.domains)} | domains with all six organs named |",
    ])


def render_domains(spine) -> str:
    rows = [
        "| Domain | The loop in one line | Control maturity |",
        "|---|---|---|",
    ]
    for d in spine.domains:
        line = " ".join(str(d.get("loop_in_one_line", "")).split())
        rows.append(f"| **{d['name']}** | {line} | `{d.get('maturity','')}` |")
    return "\n".join(rows)


def render_corpus(spine, report) -> str:
    return "\n".join([
        "| Node kind | Count | What it holds |",
        "|---|---:|---|",
        f"| concepts | {len(spine.concepts)} | control ideas, each mapped to a loop organ |",
        f"| people | {len(spine.people)} | contributors, each owning exactly one concept |",
        f"| works | {len(spine.works)} | papers and books, each with a resolvable citation |",
        f"| labs | {len(spine.labs)} | groups that own a line of work |",
        f"| applications | {len(spine.applications)} | deployed loops, with the guarantee actually claimed |",
        f"| questions | {len(spine.questions)} | open problems and honest progress |",
        f"| claims | {len(spine.claims)} | assertions the gate judges |",
        f"| loop cards | {len(spine.loops)} | systems mapped onto the six organs |",
        f"| **graph** | **{report.nodes} nodes / {report.edges} edges** | the knowledge base, typed and reachability-gated |",
    ])


def render_catches(spine, gate) -> str:
    """The gate's most instructive catches — chosen deterministically, never sampled."""
    verdicts = {v.claim_id: v for v in gate.judge_all(spine.claims)}
    picks = [
        "mpc-humanoid-safe", "rlhf-aligned", "self-refine-improves",
        "lqg-optimal-safe", "agent-loop-reliable", "eval-measures-safety",
    ]
    rows = ["| Claim | Asserted | Earned | What held it back |", "|---|:--:|:--:|---|"]
    for pid in picks:
        v = verdicts.get(pid)
        if v is None:
            continue
        rows.append(
            f"| {v.mark} `{pid}` | {v.claimed.code} | **{v.effective.code}** | {v.limiting or '—'} |"
        )
    return "\n".join(rows)


def build_blocks() -> dict[str, str]:
    spine = Registry(ROOT).load()
    gate = ControlClaimGate()
    report = build_graph(spine).check()
    return {
        "metrics": render_metrics(spine, gate, report),
        "domains": render_domains(spine),
        "corpus": render_corpus(spine, report),
        "catches": render_catches(spine, gate),
    }


def apply_blocks(text: str, blocks: dict[str, str]) -> str:
    for name, body in blocks.items():
        begin, end = _block(name, body)
        pattern = re.compile(
            re.escape(begin) + r".*?" + re.escape(end), re.DOTALL
        )
        if not pattern.search(text):
            raise SystemExit(
                f"✗ readme: no <!-- BEGIN:{name} --> … <!-- END:{name} --> block in README.md"
            )
        text = pattern.sub(f"{begin}\n{body}\n{end}", text)
    return text


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="fail on drift instead of writing")
    args = parser.parse_args()

    if not README.is_file():
        print("✗ readme: README.md not found", file=sys.stderr)
        return 1

    current = README.read_text(encoding="utf-8")
    updated = apply_blocks(current, build_blocks())

    if args.check:
        if current != updated:
            print(
                "✗ readme: generated blocks have drifted from data/. Run `make readme`.",
                file=sys.stderr,
            )
            return 1
        print("✓ readme: generated blocks match data/")
        return 0

    if current != updated:
        README.write_text(updated, encoding="utf-8")
        print("✓ readme: regenerated")
    else:
        print("✓ readme: already current")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
