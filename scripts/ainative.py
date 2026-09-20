#!/usr/bin/env python3
"""Self-audit — score HOW this repo operates, with in-repo evidence.

A regression in operating discipline should fail the build exactly like a code regression.
Each principle in ``data/ainative.yml`` names files that must exist; the score is the
fraction of principles whose evidence is entirely present, gated at the declared threshold.

This is deliberately crude. It cannot tell whether ``tools/layers.py`` is any GOOD — only
that the repo still has the organ it claims to have. Organ loss is the failure mode it
catches, and it is a real one.
"""

from __future__ import annotations

import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    spec = yaml.safe_load((ROOT / "data" / "ainative.yml").read_text(encoding="utf-8"))
    principles = spec.get("principles", [])
    threshold = int(spec.get("threshold", 90))
    if not principles:
        print("✗ ainative: no principles declared", file=sys.stderr)
        return 1

    held, failures = 0, []
    for principle in principles:
        missing = [p for p in principle.get("evidence", ()) if not (ROOT / p).exists()]
        if missing:
            failures.append((principle["id"], missing))
        else:
            held += 1

    score = round(100 * held / len(principles))
    for pid, missing in failures:
        print(f"  ✗ {pid}: missing evidence {missing}", file=sys.stderr)

    if score < threshold:
        print(f"✗ ainative: {score}/100 ({held}/{len(principles)}), need ≥ {threshold}",
              file=sys.stderr)
        return 1
    print(f"✓ ainative: {score}/100 — {held}/{len(principles)} principles hold their evidence")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
