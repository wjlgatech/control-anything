"""The numbers this repo published in prose, asserted here.

Any number in prose is a claim; the scorer is the measurement; a test must assert they
agree. The long-form article at agentic-portfolio states three figures about this corpus,
and a reader who runs `make check` is entitled to get the same ones back.

If a number here legitimately changes because the corpus grew, update BOTH this file and
the article in the same change. That coupling is the point: it makes silent drift between
what we publish and what we compute impossible rather than merely unlikely.
"""

from __future__ import annotations

import pytest

from control_anything.core.claim_gate import ControlClaimGate
from control_anything.core.registry import Registry

#: What the published article asserts, verbatim.
PUBLISHED = {
    "claims": 32,          # "wrote out 32 safety claims"
    "caught": 30,          # "capped or refused 30 of the 32"
    "unverified_rate": 0.53,  # "an unverified_rate of 0.53"
}

ARTICLE = "https://agentic-portfolio-lovat.vercel.app/articles/assumption-ledger.html"


@pytest.fixture(scope="module")
def stats():
    return ControlClaimGate().stats(Registry().load().claims)


def test_published_claim_count(stats):
    assert stats.total == PUBLISHED["claims"], (
        f"The article ({ARTICLE}) says {PUBLISHED['claims']} claims; the corpus now has "
        f"{stats.total}. Update both, in the same change."
    )


def test_published_caught_count(stats):
    caught = stats.capped + stats.refused
    assert caught == PUBLISHED["caught"], (
        f"The article says the gate caught {PUBLISHED['caught']} over-claims; it now "
        f"catches {caught}. Update both, in the same change."
    )


def test_published_unverified_rate(stats):
    """Published to two decimal places, so compare at that precision."""
    assert round(stats.unverified_rate, 2) == PUBLISHED["unverified_rate"], (
        f"The article says unverified_rate is {PUBLISHED['unverified_rate']}; it is now "
        f"{round(stats.unverified_rate, 2)}. Update both, in the same change."
    )


def test_the_articles_worked_example_still_computes_as_printed():
    """The figure in the article shows mpc-humanoid-safe capped G3 -> G1. Assert it."""
    spine = Registry().load()
    claim = next(c for c in spine.claims if c.id == "mpc-humanoid-safe")
    verdict = ControlClaimGate().judge(claim)
    assert verdict.claimed.code == "G3"
    assert verdict.effective.code == "G1"
    assert verdict.limiting == "assumption:mpc-model-match"
