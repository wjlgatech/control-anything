"""Tests over the real spine and the knowledge graph.

These run against ``data/*.yml`` rather than fixtures on purpose: the spine IS the product,
so a corpus that drifts out of shape should fail the build exactly like broken code.
"""

from __future__ import annotations

import pytest

from control_anything.core.claim_gate import ControlClaimGate
from control_anything.core.graph import build_graph
from control_anything.core.models import LoopCard, Organ, SpineError
from control_anything.core.registry import Registry


@pytest.fixture(scope="module")
def spine():
    return Registry().load()


@pytest.fixture(scope="module")
def graph(spine):
    return build_graph(spine)


# --------------------------------------------------------------------------------------
# LoopCard
# --------------------------------------------------------------------------------------


def test_every_domain_has_a_loop_card(spine):
    """The stopping rule from GOAL.md §0, enforced."""
    covered = {loop.domain for loop in spine.loops}
    missing = spine.domain_ids() - covered
    assert not missing, f"domains with no LoopCard: {sorted(missing)}"


def test_every_loop_card_names_all_six_organs(spine):
    for loop in spine.loops:
        for organ in Organ:
            assert loop.organ(organ).strip(), f"{loop.id} has a blank {organ.value}"


def test_every_loop_card_is_complete(spine):
    """latency, authority and fallback are where real systems fail."""
    incomplete = {loop.id: loop.gaps for loop in spine.loops if not loop.is_complete}
    assert not incomplete, f"incomplete loop cards: {incomplete}"


def test_a_loop_card_missing_an_organ_is_rejected():
    with pytest.raises(SpineError, match="missing organs"):
        LoopCard(
            id="broken",
            system="a system with no sensor",
            domain="agentic",
            organs={o: "x" for o in Organ if o is not Organ.SENSOR},
        )


def test_a_loop_card_with_a_blank_organ_is_rejected():
    with pytest.raises(SpineError, match="blank organs"):
        LoopCard(
            id="broken",
            system="s",
            domain="agentic",
            organs={**{o: "x" for o in Organ}, Organ.SENSOR: "   "},
        )


# --------------------------------------------------------------------------------------
# graph invariants
# --------------------------------------------------------------------------------------


def test_no_orphan_nodes(graph):
    report = graph.check()
    assert not report.orphans, f"orphans: {list(report.orphans)[:10]}"


def test_gate_coverage_is_total(graph):
    """No claim may reach output without passing the gate."""
    assert graph.check().gate_coverage == 1.0


def test_every_concept_maps_to_a_loop_organ(graph):
    report = graph.check()
    assert not report.unmapped_concepts, f"unmapped: {list(report.unmapped_concepts)}"


def test_graph_is_deterministic(spine):
    """Same spine, byte-identical graph — required for drift-gating generated docs."""
    a, b = build_graph(spine).check(), build_graph(spine).check()
    assert a.nodes == b.nodes and a.edges == b.edges
    assert a.kind_counts == b.kind_counts


def test_trace_reaches_concepts_from_a_claim(graph, spine):
    """`ca trace` must actually work on the real corpus."""
    traced = [
        c.id for c in spine.claims
        if graph.trace(f"claim:{c.id}", "concept")
    ]
    assert len(traced) >= len(spine.claims) // 2


# --------------------------------------------------------------------------------------
# the gate, over the real corpus
# --------------------------------------------------------------------------------------


def test_the_gate_actually_catches_overclaims(spine):
    """GOAL.md §0: if `capped` is 0 the gate is decorative and the repo failed its thesis."""
    stats = ControlClaimGate().stats(spine.claims)
    caught = stats.capped + stats.refused
    assert caught >= 12, f"gate caught only {caught} over-claims; see GOAL.md §0"


def test_the_gate_also_lets_some_claims_stand(spine):
    """A gate that refuses everything is as useless as one that refuses nothing."""
    stats = ControlClaimGate().stats(spine.claims)
    assert stats.passed >= 1, "no claim passed — the gate is a wrecking ball, not a referee"


def test_every_capped_claim_names_what_limited_it(spine):
    gate = ControlClaimGate()
    for verdict in gate.judge_all(spine.claims):
        if verdict.was_capped:
            assert verdict.limiting, f"{verdict.claim_id} capped with no limiting cause"
            assert verdict.reasons, f"{verdict.claim_id} capped with no reason"


def test_unverified_rate_is_published_not_hidden(spine):
    """The number must exist and be in range; the README prints it."""
    rate = ControlClaimGate().stats(spine.claims).unverified_rate
    assert 0.0 <= rate <= 1.0


def test_analogy_claims_never_reach_robust(spine):
    """The rigorous/analogy split is the repo's sharpest edge. It must hold on real data."""
    gate = ControlClaimGate()
    for claim, verdict in zip(spine.claims, gate.judge_all(spine.claims)):
        if claim.bridge == "analogy":
            assert verdict.effective < 3, (
                f"{claim.id} is tagged analogy but reached {verdict.effective.code}"
            )


# --------------------------------------------------------------------------------------
# referential integrity
# --------------------------------------------------------------------------------------


def test_every_work_cites_something_checkable(spine):
    for work in spine.works:
        assert any(work.get(k) for k in ("doi", "arxiv", "url", "source")), work["id"]


def test_every_person_owns_exactly_one_concept(spine):
    concept_ids = spine.concept_ids()
    for person in spine.people:
        owned = person.get("owns_concept")
        assert owned, f"{person['id']} owns no concept"
        assert owned in concept_ids, f"{person['id']} owns unknown concept {owned!r}"


def test_no_dangling_foreign_keys(spine):
    """Registry validates on load; this asserts the load actually happened."""
    assert spine.domains and spine.concepts and spine.claims and spine.loops
