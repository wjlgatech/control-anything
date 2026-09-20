"""ControlClaimGate — the repo's thesis, made executable.

**The one rule:** a control claim is worth exactly the weakest assumption holding it up.

A claim arrives asserting a guarantee level. The gate ignores that assertion and computes
what the claim has actually *earned*, by taking the minimum of three ceilings:

1. what its **assumptions** permit (an unchecked assumption caps you at "we measured it"),
2. what its **evidence type** permits (an analogy cannot carry a proof),
3. what was **claimed** (the gate never promotes — it is a referee, not a booster).

The gap between claimed and effective is the ``capped`` signal. If no claim in the corpus
is ever capped, the gate is decorative and the repo has failed its own thesis — which is
why ``scripts/gate.py --stats`` prints that count and ``make check`` gates on it.

Worked example, the one this repo exists for::

    claim:  "our MPC keeps the humanoid upright"   claimed: G3 (robust)
    assumptions:
      - "the dynamics model matches the real robot"        status: assumed
      - "the solver returns within 10 ms"                  status: monitored (watchdog -> sit)
    ->  assumption ceiling = min(G1, G3) = G1
    ->  effective = G1 (empirical), capped from G3, load-bearing: the dynamics model

That is "we used an MPC, therefore it is safe" caught by arithmetic rather than by taste.

Maker-is-not-checker: this module *only* judges. Nothing here constructs claims or edits
the spine; ``registry.py`` loads and ``scripts/`` prints. Keeping the referee separate from
the generator is what lets tests hold them against each other.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Sequence

from .models import (
    Assumption,
    Claim,
    EvidenceType,
    GuaranteeLevel,
)

__all__ = ["Verdict", "ControlClaimGate", "GateStats"]


# The symbol printed for each outcome. Kept here so every surface agrees.
_MARKS = {
    "pass": "✅",
    "capped": "🟡",
    "refused": "⛔",
    "unproven": "⚪",
}


@dataclass(frozen=True, slots=True)
class Verdict:
    """What the gate decided about one claim, and why.

    ``reasons`` is always populated — a verdict that cannot explain itself is not reviewable,
    and review by strangers is the whole point of the community organ.
    """

    claim_id: str
    claimed: GuaranteeLevel
    effective: GuaranteeLevel
    outcome: str                      # pass | capped | refused | unproven
    limiting: str | None              # what held it back: assumption id, or 'evidence:<type>'
    reasons: Sequence[str]

    @property
    def mark(self) -> str:
        """The status symbol for tables and CLI output."""
        return _MARKS[self.outcome]

    @property
    def was_capped(self) -> bool:
        """True when the claim asserted more than it earned."""
        return self.effective < self.claimed

    @property
    def headline(self) -> str:
        """One line a human can read in a PR diff."""
        if self.effective == self.claimed:
            return f"{self.mark} {self.claim_id}: {self.claimed.code} held"
        return (
            f"{self.mark} {self.claim_id}: claimed {self.claimed.code} -> "
            f"effective {self.effective.code} ({self.effective.plain})"
            + (f", limited by {self.limiting}" if self.limiting else "")
        )

    def explain(self) -> str:
        """Full multi-line explanation: the headline plus every reason."""
        return "\n".join([self.headline, *(f"    - {r}" for r in self.reasons)])


@dataclass(frozen=True, slots=True)
class GateStats:
    """Aggregate numbers over a corpus — the metrics GOAL.md promises to gate on."""

    total: int
    passed: int
    capped: int
    refused: int
    unproven: int
    verified: int

    @property
    def unverified_rate(self) -> float:
        """Fraction of claims whose source was never resolved against a primary.

        Published in the README rather than hidden; ``0.0`` for an empty corpus so the
        number is always well-defined.
        """
        if self.total == 0:
            return 0.0
        return round((self.total - self.verified) / self.total, 4)

    def as_dict(self) -> dict[str, float | int]:
        """Stable ordering — this feeds drift-gated generated docs."""
        return {
            "total": self.total,
            "passed": self.passed,
            "capped": self.capped,
            "refused": self.refused,
            "unproven": self.unproven,
            "verified": self.verified,
            "unverified_rate": self.unverified_rate,
        }


class ControlClaimGate:
    """Judge control claims against their assumptions and evidence.

    Deterministic and offline by construction: no clock, no network, no randomness. The
    same corpus gives byte-identical verdicts on every machine, which is what makes the
    generated README sections drift-checkable.

    :param require_evidence: when True (default) a claim above G0 with no evidence at all
        is ``unproven`` rather than merely capped. "No evidence means no" — an unmeasured
        item is excluded, never given a quiet pass.
    :param require_assumptions: when True (default) a claim at G2 or above must name at
        least one assumption. A strong guarantee that rests on nothing has not been
        analysed; it has been asserted.
    """

    def __init__(
        self,
        *,
        require_evidence: bool = True,
        require_assumptions: bool = True,
    ) -> None:
        self.require_evidence = require_evidence
        self.require_assumptions = require_assumptions

    # -- the three ceilings ------------------------------------------------------------

    @staticmethod
    def assumption_ceiling(assumptions: Sequence[Assumption]) -> GuaranteeLevel:
        """Strongest guarantee the assumption set permits.

        With no assumptions the set imposes no ceiling (``G4``) — the *separate*
        ``require_assumptions`` check is what stops a bare claim sailing through, so that
        "named no assumptions" and "named only safe assumptions" stay distinguishable.
        """
        if not assumptions:
            return GuaranteeLevel.CERTIFIED
        return min((a.ceiling for a in assumptions), default=GuaranteeLevel.CERTIFIED)

    @staticmethod
    def evidence_ceiling(evidence: Sequence[EvidenceType]) -> GuaranteeLevel:
        """Strongest guarantee the evidence permits.

        Note the *max*: evidence kinds combine by taking your **best** support, unlike
        assumptions which combine by your **worst** link. A hardware result is not weakened
        by also having an analogy; a proof is not weakened by also having a benchmark.
        """
        if not evidence:
            return GuaranteeLevel.ANECDOTE
        return max(e.ceiling for e in evidence)

    # -- the verdict -------------------------------------------------------------------

    def judge(self, claim: Claim) -> Verdict:
        """Compute the effective guarantee for one claim."""
        reasons: list[str] = []

        a_ceiling = self.assumption_ceiling(claim.assumptions)
        e_ceiling = self.evidence_ceiling(claim.evidence)
        effective = min(claim.claimed, a_ceiling, e_ceiling)

        limiting: str | None = None
        weakest = claim.weakest_assumption

        # Which ceiling actually bound? Assumptions are reported first when they tie,
        # because a load-bearing assumption is the more actionable finding.
        if a_ceiling <= e_ceiling and a_ceiling < claim.claimed and weakest is not None:
            limiting = f"assumption:{weakest.id}"
            reasons.append(
                f"assumption {weakest.id!r} is {weakest.status.value} "
                f"({weakest.statement}) -> caps at {a_ceiling.code}"
            )
        elif e_ceiling < claim.claimed:
            best = max(claim.evidence, key=lambda e: int(e.ceiling)) if claim.evidence else None
            limiting = f"evidence:{best.value}" if best else "evidence:none"
            reasons.append(
                f"strongest evidence is {best.value if best else 'none'} -> caps at {e_ceiling.code}"
            )

        # Refusals: structural failures that are worse than a cap.
        if any(a.status.ceiling == GuaranteeLevel.ANECDOTE for a in claim.assumptions):
            violated = sorted(
                a.id for a in claim.assumptions
                if a.status.ceiling == GuaranteeLevel.ANECDOTE
            )
            reasons.append(f"violated assumption(s): {violated} -> claim refused")
            return Verdict(
                claim_id=claim.id,
                claimed=claim.claimed,
                effective=GuaranteeLevel.ANECDOTE,
                outcome="refused",
                limiting=f"assumption:{violated[0]}",
                reasons=tuple(reasons),
            )

        # Unproven: asserted above anecdote with nothing behind it at all.
        if self.require_evidence and claim.claimed > GuaranteeLevel.ANECDOTE and not claim.evidence:
            reasons.append(
                "no evidence named; an unmeasured claim is excluded, not quietly passed"
            )
            return Verdict(
                claim_id=claim.id,
                claimed=claim.claimed,
                effective=GuaranteeLevel.ANECDOTE,
                outcome="unproven",
                limiting="evidence:none",
                reasons=tuple(reasons),
            )

        if (
            self.require_assumptions
            and claim.claimed >= GuaranteeLevel.STATISTICAL
            and not claim.assumptions
        ):
            reasons.append(
                f"claims {claim.claimed.code} but names no assumptions; a guarantee that "
                "rests on nothing has been asserted, not analysed"
            )
            return Verdict(
                claim_id=claim.id,
                claimed=claim.claimed,
                effective=GuaranteeLevel.EMPIRICAL,
                outcome="capped",
                limiting="assumptions:none",
                reasons=tuple(reasons),
            )

        # An analogy dressed as a theorem is its own failure mode.
        if claim.bridge == "analogy" and claim.claimed >= GuaranteeLevel.ROBUST:
            reasons.append(
                "bridge is tagged 'analogy' but claims a robust/certified guarantee; "
                "a structural metaphor cannot carry a guarantee"
            )
            return Verdict(
                claim_id=claim.id,
                claimed=claim.claimed,
                effective=GuaranteeLevel.ANECDOTE,
                outcome="refused",
                limiting="bridge:analogy",
                reasons=tuple(reasons),
            )

        if effective < claim.claimed:
            return Verdict(
                claim_id=claim.id,
                claimed=claim.claimed,
                effective=effective,
                outcome="capped",
                limiting=limiting,
                reasons=tuple(reasons),
            )

        reasons.append(
            f"assumptions permit {a_ceiling.code}, evidence permits {e_ceiling.code}; "
            f"{claim.claimed.code} holds"
        )
        return Verdict(
            claim_id=claim.id,
            claimed=claim.claimed,
            effective=effective,
            outcome="pass",
            limiting=None,
            reasons=tuple(reasons),
        )

    # -- corpus level ------------------------------------------------------------------

    def judge_all(self, claims: Iterable[Claim]) -> list[Verdict]:
        """Judge a corpus, in input order (deterministic)."""
        return [self.judge(c) for c in claims]

    def stats(self, claims: Iterable[Claim]) -> GateStats:
        """Aggregate the corpus into the numbers GOAL.md gates on."""
        claim_list = list(claims)
        verdicts = self.judge_all(claim_list)
        outcomes = [v.outcome for v in verdicts]
        return GateStats(
            total=len(claim_list),
            passed=outcomes.count("pass"),
            capped=outcomes.count("capped"),
            refused=outcomes.count("refused"),
            unproven=outcomes.count("unproven"),
            verified=sum(1 for c in claim_list if c.verified),
        )
