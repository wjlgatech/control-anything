"""Tests for the README contract gate.

The gate exists because `docs/REPO_PLAYBOOK.md` §0 prescribed files and not README content.
These tests exist because a gate that cannot fail is decorative — which is this repo's own
thesis, applied to its own tooling.

The mutation tests at the bottom matter most: each removes one section from a passing README
and asserts the score drops. Without them, a regex that matches nothing would look identical
to a repo that passes.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def _load_gate():
    """Import the gate by path — it is a tool, not a package module."""
    spec = importlib.util.spec_from_file_location(
        "readme_contract", ROOT / "tools" / "readme_contract.py"
    )
    module = importlib.util.module_from_spec(spec)
    # Register before exec: dataclasses resolves __module__ through sys.modules.
    import sys
    sys.modules["readme_contract"] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def gate():
    return _load_gate()


@pytest.fixture(scope="module")
def readme() -> str:
    return (ROOT / "README.md").read_text(encoding="utf-8")


def test_the_readme_satisfies_every_contract_item(gate, readme):
    results, score = gate.evaluate(readme)
    missing = [item.key for item, ok, _ in results if not ok]
    assert not missing, f"README is missing: {missing}"
    assert score == 100


def test_the_floor_is_recorded_and_matches(gate, readme):
    floor = json.loads((ROOT / "data" / "readme-floor.json").read_text())["readme_contract"]
    _, score = gate.evaluate(readme)
    assert score >= floor, f"README scored {score}, below the recorded floor {floor}"


def test_the_contract_has_eleven_items(gate):
    """Pinned: changing the contract is a deliberate act, not a drive-by edit."""
    assert len(gate.CONTRACT) == 11


def test_every_contract_item_states_its_readers_question(gate):
    for item in gate.CONTRACT:
        assert item.question.strip().endswith("?"), f"{item.key} does not ask a question"


# --------------------------------------------------------------------------------------
# MUTATION TESTS — remove a section, prove the gate notices
# --------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "heading",
    ["## What you can swap (the seams)", "## Docs", "## Provenance", "## Tested to the gate"],
)
def test_removing_a_section_drops_the_score(gate, readme, heading):
    """If deleting a whole section leaves the score unchanged, the check is not checking."""
    assert heading in readme, f"fixture drift: {heading!r} no longer in README"
    start = readme.index(heading)
    end = readme.find("\n## ", start + 1)
    mutated = readme[:start] + (readme[end:] if end != -1 else "")
    _, mutated_score = gate.evaluate(mutated)
    _, real_score = gate.evaluate(readme)
    assert mutated_score < real_score, f"removing {heading!r} did not lower the score"


def test_a_mental_model_without_a_diagram_fails(gate):
    """The sharpest item: prose is not a mental model. Removing the diagram must fail."""
    prose_only = (
        "# A repo\n\nIt does a thing that is worth several words of explanation here.\n\n"
        "## The mental model\n\nIt is like a thermostat, and here is a long paragraph "
        "explaining that at length without ever drawing anything at all.\n"
    )
    results, _ = gate.evaluate(prose_only)
    by_key = {item.key: (ok, why) for item, ok, why in results}
    ok, why = by_key["mentalmodel"]
    assert not ok and "DIAGRAM" in why


def test_a_heading_alone_does_not_satisfy_the_contract(gate):
    """A table of contents must not pass. This is the distinction the gate exists for."""
    headings_only = "\n".join(
        ["# Repo", "Some words that go on for at least eight of them in total here."]
        + [f"## {item.key}" for item in gate.CONTRACT]
    )
    _, score = gate.evaluate(headings_only)
    assert score < 60, f"a bare table of contents scored {score}"
