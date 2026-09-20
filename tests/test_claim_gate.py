"""Tests for ControlClaimGate — the repo's thesis, held to account.

The important tests here are the MUTATION tests at the bottom. A gate that passes its own
happy-path tests proves nothing; a gate that still passes when you break it proves it was
never checking. Each mutation test breaks the capping rule in a different way and asserts
the suite notices.
"""

from __future__ import annotations

import pytest

from control_anything.core.claim_gate import ControlClaimGate
from control_anything.core.models import (
    Assumption,
    AssumptionStatus,
    Claim,
    EvidenceType,
    GuaranteeLevel,
    SpineError,
)


def assumption(status: AssumptionStatus, ident: str = "a1") -> Assumption:
    """An assumption of the given status, with a check when the status demands one."""
    needs_check = status in {AssumptionStatus.MONITORED, AssumptionStatus.DISCHARGED}
    return Assumption(
        id=ident,
        statement=f"test assumption {ident}",
        status=status,
        check="a named check" if needs_check else None,
    )


def claim(**kwargs) -> Claim:
    base = dict(
        id="c1",
        statement="a test claim",
        claimed=GuaranteeLevel.ROBUST,
        evidence=(EvidenceType.HARDWARE,),
        assumptions=(assumption(AssumptionStatus.DISCHARGED),),
    )
    base.update(kwargs)
    return Claim(**base)


# --------------------------------------------------------------------------------------
# the ladder
# --------------------------------------------------------------------------------------


def test_guarantee_levels_are_ordered():
    """min() over levels must be meaningful — the whole cap is built on it."""
    assert GuaranteeLevel.ANECDOTE < GuaranteeLevel.EMPIRICAL < GuaranteeLevel.STATISTICAL
    assert GuaranteeLevel.STATISTICAL < GuaranteeLevel.ROBUST < GuaranteeLevel.CERTIFIED
    assert min(GuaranteeLevel.CERTIFIED, GuaranteeLevel.EMPIRICAL) is GuaranteeLevel.EMPIRICAL


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("G3", GuaranteeLevel.ROBUST),
        ("robust", GuaranteeLevel.ROBUST),
        (3, GuaranteeLevel.ROBUST),
        ("  CERTIFIED  ", GuaranteeLevel.CERTIFIED),
    ],
)
def test_guarantee_parse_accepts_spine_spellings(raw, expected):
    assert GuaranteeLevel.parse(raw) is expected


@pytest.mark.parametrize("raw", ["G5", "G-1", 7, "vibes", None, True])
def test_guarantee_parse_rejects_nonsense(raw):
    with pytest.raises(SpineError):
        GuaranteeLevel.parse(raw)


def test_assumption_status_ceilings_are_the_design_judgement():
    """These four numbers ARE the repo's central claim. Pin them."""
    assert AssumptionStatus.VIOLATED.ceiling is GuaranteeLevel.ANECDOTE
    assert AssumptionStatus.ASSUMED.ceiling is GuaranteeLevel.EMPIRICAL
    assert AssumptionStatus.MONITORED.ceiling is GuaranteeLevel.ROBUST
    assert AssumptionStatus.DISCHARGED.ceiling is GuaranteeLevel.CERTIFIED


# --------------------------------------------------------------------------------------
# the assumption ledger
# --------------------------------------------------------------------------------------


def test_monitored_assumption_must_name_its_check():
    """An unnamed check is a wish. This is the rule that keeps the ledger honest."""
    with pytest.raises(SpineError, match="names no check"):
        Assumption(id="x", statement="something", status=AssumptionStatus.MONITORED)


def test_discharged_assumption_must_name_its_check():
    with pytest.raises(SpineError, match="names no check"):
        Assumption(id="x", statement="something", status=AssumptionStatus.DISCHARGED)


def test_assumed_assumption_needs_no_check():
    """`assumed` is the honest 'we have not checked this' — it must stay easy to write."""
    a = Assumption(id="x", statement="something", status=AssumptionStatus.ASSUMED)
    assert a.check is None
    assert a.is_load_bearing


def test_weakest_assumption_is_deterministic_under_ties():
    """Byte-stable output is a hard requirement for drift-gating generated docs."""
    c = claim(assumptions=(
        assumption(AssumptionStatus.ASSUMED, "zzz"),
        assumption(AssumptionStatus.ASSUMED, "aaa"),
    ))
    assert c.weakest_assumption.id == "aaa"


# --------------------------------------------------------------------------------------
# the cap — the core behaviour
# --------------------------------------------------------------------------------------


def test_an_assumed_assumption_caps_a_robust_claim_at_empirical():
    """THE test. 'We used an MPC, therefore it is safe' caught by arithmetic."""
    verdict = ControlClaimGate().judge(
        claim(claimed=GuaranteeLevel.ROBUST,
              assumptions=(assumption(AssumptionStatus.ASSUMED),))
    )
    assert verdict.outcome == "capped"
    assert verdict.effective is GuaranteeLevel.EMPIRICAL
    assert verdict.was_capped
    assert "a1" in verdict.limiting


def test_the_weakest_assumption_sets_the_cap_not_the_average():
    """One unchecked assumption among many good ones still caps the claim."""
    verdict = ControlClaimGate().judge(
        claim(
            claimed=GuaranteeLevel.CERTIFIED,
            evidence=(EvidenceType.PROOF,),
            assumptions=(
                assumption(AssumptionStatus.DISCHARGED, "good1"),
                assumption(AssumptionStatus.DISCHARGED, "good2"),
                assumption(AssumptionStatus.ASSUMED, "weak"),
            ),
        )
    )
    assert verdict.effective is GuaranteeLevel.EMPIRICAL
    assert verdict.limiting == "assumption:weak"


def test_a_violated_assumption_refuses_rather_than_caps():
    verdict = ControlClaimGate().judge(
        claim(assumptions=(assumption(AssumptionStatus.VIOLATED),))
    )
    assert verdict.outcome == "refused"
    assert verdict.effective is GuaranteeLevel.ANECDOTE


def test_all_discharged_assumptions_let_the_claim_stand():
    """The gate is a referee, not a wrecking ball."""
    verdict = ControlClaimGate().judge(
        claim(claimed=GuaranteeLevel.CERTIFIED, evidence=(EvidenceType.PROOF,))
    )
    assert verdict.outcome == "pass"
    assert verdict.effective is GuaranteeLevel.CERTIFIED
    assert not verdict.was_capped


def test_the_gate_never_promotes():
    """A modest claim with overwhelming evidence stays modest."""
    verdict = ControlClaimGate().judge(
        claim(claimed=GuaranteeLevel.EMPIRICAL, evidence=(EvidenceType.PROOF,))
    )
    assert verdict.effective is GuaranteeLevel.EMPIRICAL
    assert verdict.outcome == "pass"


# --------------------------------------------------------------------------------------
# evidence
# --------------------------------------------------------------------------------------


def test_evidence_combines_by_best_not_worst():
    """Unlike assumptions: a proof is not weakened by also having an analogy."""
    gate = ControlClaimGate()
    ceiling = gate.evidence_ceiling((EvidenceType.ANALOGY, EvidenceType.PROOF))
    assert ceiling is GuaranteeLevel.CERTIFIED


def test_analogy_alone_cannot_carry_a_guarantee():
    verdict = ControlClaimGate().judge(
        claim(claimed=GuaranteeLevel.STATISTICAL, evidence=(EvidenceType.ANALOGY,))
    )
    assert verdict.effective is GuaranteeLevel.ANECDOTE
    assert verdict.limiting == "evidence:analogy"


def test_no_evidence_means_unproven_not_a_quiet_pass():
    verdict = ControlClaimGate().judge(
        claim(claimed=GuaranteeLevel.ROBUST, evidence=())
    )
    assert verdict.outcome == "unproven"


def test_a_strong_claim_with_no_assumptions_is_capped():
    """A guarantee resting on nothing has been asserted, not analysed."""
    verdict = ControlClaimGate().judge(
        claim(claimed=GuaranteeLevel.CERTIFIED, evidence=(EvidenceType.PROOF,), assumptions=())
    )
    assert verdict.outcome == "capped"
    assert verdict.limiting == "assumptions:none"


def test_an_analogy_bridge_cannot_claim_robustness():
    """Conflating a metaphor with a theorem is the failure this repo most fears."""
    verdict = ControlClaimGate().judge(
        claim(claimed=GuaranteeLevel.ROBUST, bridge="analogy")
    )
    assert verdict.outcome == "refused"
    assert verdict.limiting == "bridge:analogy"


def test_an_analogy_bridge_may_still_make_a_modest_claim():
    verdict = ControlClaimGate().judge(
        claim(claimed=GuaranteeLevel.EMPIRICAL, bridge="analogy")
    )
    assert verdict.outcome == "pass"


def test_bridge_must_be_rigorous_or_analogy():
    with pytest.raises(SpineError, match="rigorous"):
        claim(bridge="sort-of")


# --------------------------------------------------------------------------------------
# reporting
# --------------------------------------------------------------------------------------


def test_every_verdict_explains_itself():
    """A verdict nobody can review is not reviewable by strangers — the community organ dies."""
    gate = ControlClaimGate()
    for status in AssumptionStatus:
        verdict = gate.judge(claim(assumptions=(assumption(status),)))
        assert verdict.reasons, f"{status} produced no reason"
        assert verdict.explain().strip()


def test_stats_counts_every_outcome():
    gate = ControlClaimGate()
    claims = [
        claim(id="pass1", claimed=GuaranteeLevel.EMPIRICAL),
        claim(id="capped1", assumptions=(assumption(AssumptionStatus.ASSUMED),)),
        claim(id="refused1", assumptions=(assumption(AssumptionStatus.VIOLATED),)),
    ]
    stats = gate.stats(claims)
    assert stats.total == 3
    assert stats.passed == 1
    assert stats.capped == 1
    assert stats.refused == 1


def test_unverified_rate_is_well_defined_on_an_empty_corpus():
    assert ControlClaimGate().stats([]).unverified_rate == 0.0


def test_the_gate_is_deterministic():
    """No clock, no network, no randomness — same corpus, identical verdicts."""
    gate = ControlClaimGate()
    c = claim(assumptions=(
        assumption(AssumptionStatus.ASSUMED, "b"),
        assumption(AssumptionStatus.MONITORED, "a"),
    ))
    first = [gate.judge(c).explain() for _ in range(5)]
    assert len(set(first)) == 1


# --------------------------------------------------------------------------------------
# MUTATION TESTS — break the gate, prove the suite notices
# --------------------------------------------------------------------------------------


def test_mutation_ceiling_table_inverted_would_fail():
    """If ASSUMED stopped capping at empirical, the canonical over-claim would pass."""
    verdict = ControlClaimGate().judge(
        claim(claimed=GuaranteeLevel.ROBUST,
              assumptions=(assumption(AssumptionStatus.ASSUMED),))
    )
    # This assertion is what a mutation of AssumptionStatus.ceiling breaks.
    assert verdict.effective < GuaranteeLevel.ROBUST, (
        "an unchecked assumption no longer caps a robust claim — the gate is decorative"
    )


def test_mutation_using_max_instead_of_min_would_fail():
    """Assumptions must combine by WORST. max() here would hide every weak link."""
    gate = ControlClaimGate()
    ceiling = gate.assumption_ceiling((
        assumption(AssumptionStatus.DISCHARGED, "strong"),
        assumption(AssumptionStatus.ASSUMED, "weak"),
    ))
    assert ceiling is GuaranteeLevel.EMPIRICAL, (
        "assumption ceiling took the best rather than the worst link"
    )


def test_mutation_dropping_the_violated_check_would_fail():
    """A known-false assumption must refuse, never merely cap."""
    verdict = ControlClaimGate().judge(
        claim(claimed=GuaranteeLevel.CERTIFIED, evidence=(EvidenceType.PROOF,),
              assumptions=(assumption(AssumptionStatus.VIOLATED),))
    )
    assert verdict.outcome == "refused", "a violated assumption no longer refuses the claim"


def test_mutation_allowing_an_uncheckable_monitor_would_fail():
    """Removing the check requirement would let any claim buy robustness for free."""
    with pytest.raises(SpineError):
        Assumption(id="x", statement="s", status=AssumptionStatus.MONITORED, check="")
