#!/usr/bin/env python3
"""Spine gate — the data loads, every reference resolves, nothing is silently missing.

This is the first gate in ``make check`` because everything else reads the spine. A broken
spine should fail here with a message naming the file and the row, not three gates later
with a traceback.

Exit codes: ``0`` green, ``1`` a spine problem, ``2`` the gate itself could not run.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from control_anything.core.models import Organ, SpineError  # noqa: E402
from control_anything.core.registry import Registry  # noqa: E402

REQUIRED_FILES = (
    "domains.yml", "concepts.yml", "people.yml", "works.yml", "labs.yml",
    "questions.yml", "applications.yml", "loops.yml", "claims.yml",
)


def main() -> int:
    problems: list[str] = []

    missing = [f for f in REQUIRED_FILES if not (ROOT / "data" / f).is_file()]
    if missing:
        print(f"✗ spine: missing data files: {missing}", file=sys.stderr)
        return 1

    try:
        spine = Registry(ROOT).load()
    except SpineError as exc:
        print(f"✗ spine: {exc}", file=sys.stderr)
        return 1

    # Every domain in the closed set must carry at least one concept and one loop card.
    # A domain with no loop is a category, and categories are what this repo refuses to be.
    loops_by_domain = {loop.domain for loop in spine.loops}
    for domain in spine.domains:
        did = str(domain["id"])
        if not (domain.get("concepts") or ()):
            problems.append(f"domain {did!r} names no concepts")
        if did not in loops_by_domain:
            problems.append(
                f"domain {did!r} has no LoopCard — if you cannot name its six organs, "
                "it does not belong in the closed set (see GOAL.md §0 stopping rule)"
            )

    # Concepts must map to at least one organ, or the ontology has a hole.
    organ_values = {o.value for o in Organ}
    for concept in spine.concepts:
        organs = concept.get("organs") or ()
        if not organs:
            problems.append(f"concept {concept['id']!r} maps to no loop organ")
        for organ in organs:
            if str(organ) not in organ_values:
                problems.append(
                    f"concept {concept['id']!r} maps to unknown organ {organ!r}"
                )

    # A work without a year cannot be placed on a timeline; a work without a source
    # cannot be checked by a stranger. Both are required for the community organ to work.
    for work in spine.works:
        if not work.get("year"):
            problems.append(f"work {work['id']!r} has no year")
        if not any(work.get(k) for k in ("source", "doi", "arxiv", "url")):
            problems.append(
                f"work {work['id']!r} names no source/doi/arxiv/url — an uncheckable citation"
            )

    if problems:
        print(f"✗ spine: {len(problems)} problem(s)", file=sys.stderr)
        for problem in problems:
            print(f"    - {problem}", file=sys.stderr)
        return 1

    print(
        f"✓ spine: {len(spine.domains)} domains · {len(spine.concepts)} concepts · "
        f"{len(spine.people)} people · {len(spine.works)} works · {len(spine.labs)} labs · "
        f"{len(spine.questions)} questions · {len(spine.applications)} applications · "
        f"{len(spine.loops)} loops · {len(spine.claims)} claims"
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:  # noqa: BLE001 - a gate must never hang the build ambiguously
        print(f"✗ spine gate crashed: {type(exc).__name__}: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc
