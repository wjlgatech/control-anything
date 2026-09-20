#!/usr/bin/env python3
"""The README contract — what a reader must be able to do after 60 seconds.

**Why this gate exists.** `docs/REPO_PLAYBOOK.md` §0 prescribes which FILES a repo has and
which gates guard them. It says almost nothing about what the README must CONTAIN. Those are
two different axes, and the playbook only had one — so a repo could be perfectly gated and
still open with a wall of prose that answers none of a stranger's questions.

Extracted 2026-09-19 from the `anyagent` README, which does this well, and generalized.
The eleven sections below are not a style preference; each answers a question a specific
reader arrives with:

    identity    what IS this?                      (everyone, first 3 seconds)
    quickstart  how do I run it right now?         (the engineer who will try it)
    mentalmodel can I picture how it works?        (the 15-year-old; needs a DIAGRAM)
    formula     what is the idea in one line?      (the person who will repeat it to someone else)
    seams       what can I swap?                   (the engineer who will extend it)
    proof       has this touched reality?          (the skeptic)
    tested      how do I know it works?            (the reviewer)
    docsindex   where is everything else?          (the returning reader)
    honest      what does it NOT do?               (the careful adopter)
    provenance  what is it made of / carrying?     (the person deciding to depend on it)
    license     may I use it?                      (legal)

A section counts as present when its heading matches AND it carries the evidence its
question demands — a mental model without a diagram is prose, a tested section without a
runnable command is a claim. That distinction is the whole point; checking headings alone
would let the contract be satisfied by a table of contents.

Exit 0 green, 1 below floor, 2 the gate could not run.
"""

from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
README = ROOT / "README.md"
FLOOR_FILE = ROOT / "data" / "readme-floor.json"


@dataclass(frozen=True)
class Section:
    """One contract item: a heading pattern plus the evidence that makes it real."""

    key: str
    question: str
    heading: str          # regex matched against headings
    evidence: str | None  # regex matched against that section's BODY; None = heading is enough
    evidence_desc: str


CONTRACT: tuple[Section, ...] = (
    Section("identity", "What IS this?",
            r"^# \S", r"\w+(?:\s+\w+){7,}", "a real sentence, not just a title"),
    Section("quickstart", "How do I run it right now?",
            r"start here|quick ?start|try it|getting started",
            r"```", "a fenced, runnable command block"),
    Section("mentalmodel", "Can I picture how it works?",
            r"mental model|how it works|the (big )?picture|six organs",
            r"```mermaid|<img|\.svg|\.png", "a DIAGRAM — prose is not a mental model"),
    Section("formula", "What is the idea in one line?",
            r"in one line|the one (thing|rule|idea)|architecture|= ",
            r"`[^`]*=[^`]*`|^> ", "a compressed identity or a pull-quote"),
    Section("seams", "What can I swap?",
            r"seam|swap|extend|plug|addon",
            r"\|.*\|.*\|", "a table naming what swaps"),
    Section("proof", "Has this touched reality?",
            r"proven|real (use ?case|application|deployment)|in the wild|what's inside",
            r"\|.*\|", "a table of real cases"),
    Section("tested", "How do I know it works?",
            r"tested|test suite|verification|gates?\b",
            r"```|`make |`pytest|`python", "the actual command to run them"),
    Section("docsindex", "Where is everything else?",
            r"docs?\b|further reading|reference",
            r"\|.*\]\(.*\)", "a table linking each doc to what is in it"),
    Section("honest", "What does it NOT do?",
            r"honest|limitation|caveat|not claim|edges",
            r"\w+(?:\s+\w+){11,}", "actual stated limits"),
    Section("provenance", "What is it made of?",
            r"provenance|what this carries|dependencies|built with",
            r"\w+(?:\s+\w+){7,}", "what it does and does not carry"),
    Section("license", "May I use it?",
            r"license", None, ""),
)


def split_sections(text: str) -> list[tuple[str, str]]:
    """Split markdown into (heading, body) pairs, keeping the H1 as the first section."""
    parts: list[tuple[str, str]] = []
    current_head, buf = "", []
    for line in text.splitlines():
        if re.match(r"^#{1,3} ", line):
            if current_head or buf:
                parts.append((current_head, "\n".join(buf)))
            current_head, buf = line, []
        else:
            buf.append(line)
    if current_head or buf:
        parts.append((current_head, "\n".join(buf)))
    return parts


def evaluate(text: str) -> tuple[list[tuple[Section, bool, str]], int]:
    """Score the README against the contract. Returns (results, score-out-of-100)."""
    sections = split_sections(text)
    results: list[tuple[Section, bool, str]] = []

    for item in CONTRACT:
        matched_body = None
        for head, body in sections:
            if re.search(item.heading, head, re.I) or (
                item.key == "identity" and re.match(item.heading, head)
            ):
                # Prefer a section whose body also satisfies the evidence test.
                if item.evidence is None or re.search(item.evidence, body, re.M):
                    matched_body = body
                    break
                if matched_body is None:
                    matched_body = body  # remember a heading-only match
        if matched_body is None:
            results.append((item, False, "section absent"))
        elif item.evidence and not re.search(item.evidence, matched_body, re.M):
            results.append((item, False, f"present but missing {item.evidence_desc}"))
        else:
            results.append((item, True, ""))

    held = sum(1 for _, ok, _ in results if ok)
    return results, round(100 * held / len(CONTRACT))


def load_floor() -> int:
    if not FLOOR_FILE.is_file():
        return 0
    try:
        return int(json.loads(FLOOR_FILE.read_text())["readme_contract"])
    except (json.JSONDecodeError, KeyError, ValueError):
        return 0


def main() -> int:
    # An explicit path makes this gate portable: point it at any repo's README to see how
    # that repo scores. That is how the contract was calibrated in the first place.
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    target = Path(args[0]) if args else README
    if not target.is_file():
        print(f"✗ readme-contract: {target} not found", file=sys.stderr)
        return 2

    results, score = evaluate(target.read_text(encoding="utf-8"))
    floor = load_floor()

    if "--bump" in sys.argv:
        FLOOR_FILE.parent.mkdir(exist_ok=True)
        FLOOR_FILE.write_text(json.dumps({"readme_contract": score}, indent=2) + "\n")
        print(f"✓ readme-contract: floor bumped to {score}")
        return 0

    for item, ok, why in results:
        mark = "✓" if ok else "✗"
        detail = "" if ok else f"  — {why}"
        print(f"  {mark} {item.key:<12} {item.question}{detail}")

    held = sum(1 for _, ok, _ in results if ok)
    print(f"\n  readme-contract: {score}/100 ({held}/{len(CONTRACT)} sections) · floor {floor}")

    if score < floor:
        print(
            f"✗ readme-contract: {score} is below the floor of {floor}. The floor only rises; "
            "lowering it is a decision-log entry, never a way to green a red build.",
            file=sys.stderr,
        )
        return 1
    print(f"✓ readme-contract: {score}/100, at or above the floor of {floor}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:  # noqa: BLE001 — a gate must fail legibly
        print(f"✗ readme-contract crashed: {type(exc).__name__}: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc
