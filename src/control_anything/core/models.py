"""Typed models for control-anything.

The whole repo rests on three ideas, in this order:

1. **Every system in scope is a feedback loop with six organs.**  ``LoopCard`` names them.
   If you cannot fill in all six, you do not have a control problem — you have a hope.
2. **Every claim about such a loop asserts a guarantee level.**  ``GuaranteeLevel`` is the
   ladder, from "it worked once in a demo" (G0) to "a machine checked the proof" (G4).
3. **A guarantee is only as strong as the assumptions holding it up.**  ``Assumption`` carries
   a *status*, and ``ControlClaimGate`` (see ``claim_gate.py``) caps the claim at what those
   statuses actually support.

Idea 3 is the repo's thesis. "We used an MPC, therefore it is safe" is the most common
over-claim in applied control, and here it is a failing exit code.

Core is stdlib + pyyaml only. No third-party imports beyond that (enforced by tools/layers.py).
"""

from __future__ import annotations

import enum
import re
from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping, Sequence

__all__ = [
    "GuaranteeLevel",
    "AssumptionStatus",
    "EvidenceType",
    "Organ",
    "Assumption",
    "LoopCard",
    "Claim",
    "Node",
    "Edge",
    "SpineError",
]


class SpineError(ValueError):
    """Raised when data in the spine (``data/*.yml``) is malformed.

    Deliberately a subclass of ``ValueError``: bad data is bad input, not a crash.
    """


# --------------------------------------------------------------------------------------
# The guarantee ladder
# --------------------------------------------------------------------------------------


class GuaranteeLevel(enum.IntEnum):
    """How strong is the promise? An ordered ladder — higher means harder to earn.

    The ordering is the point: ``IntEnum`` so ``min()`` over a set of levels is meaningful,
    which is exactly how the assumption cap is computed.

    ==== ============= ==========================================================
    Code Name          What it actually means
    ==== ============= ==========================================================
    G0   anecdote      It worked in a demo. No measurement.
    G1   empirical     Measured on a benchmark, in-distribution. No bound.
    G2   statistical   A bound with a confidence level, under stated sampling
                       assumptions (PAC, conformal prediction, a CI).
    G3   robust        Holds for every disturbance in a stated uncertainty set
                       (H-infinity, tube MPC, input-to-state stability).
    G4   certified     A machine checked a proof against a formal plant model
                       (a Lyapunov certificate, barrier-function invariance,
                       reachability analysis, a verified compiler).
    ==== ============= ==========================================================

    The jump that matters is **G1 to G2**: below it you know what happened, at or above it
    you know what *will* happen, and only within stated assumptions. Most AI safety claims
    in 2026 live at G1 while being written in the language of G3.
    """

    ANECDOTE = 0
    EMPIRICAL = 1
    STATISTICAL = 2
    ROBUST = 3
    CERTIFIED = 4

    @property
    def code(self) -> str:
        """Short form used in data files and printed tables: ``G0`` … ``G4``."""
        return f"G{int(self)}"

    @property
    def plain(self) -> str:
        """One phrase a 15-year-old can hold onto."""
        return {
            0: "it worked once",
            1: "we measured it",
            2: "we bounded it, with a confidence level",
            3: "it holds against any disturbance we listed",
            4: "a machine checked the proof",
        }[int(self)]

    @classmethod
    def parse(cls, raw: Any) -> "GuaranteeLevel":
        """Accept ``G3``, ``3``, ``"robust"``, or a ``GuaranteeLevel``. Reject everything else.

        Tolerant on the way in, strict on the way out — spine files stay readable as
        ``guarantee: robust`` while code always handles the enum.
        """
        if isinstance(raw, cls):
            return raw
        if isinstance(raw, bool):  # bool is an int subclass; catch it before the int branch
            raise SpineError(f"guarantee level cannot be a boolean: {raw!r}")
        if isinstance(raw, int):
            try:
                return cls(raw)
            except ValueError as exc:
                raise SpineError(f"guarantee level out of range 0-4: {raw!r}") from exc
        if isinstance(raw, str):
            token = raw.strip().lower()
            if re.fullmatch(r"g[0-4]", token):
                return cls(int(token[1]))
            by_name = {m.name.lower(): m for m in cls}
            if token in by_name:
                return by_name[token]
        raise SpineError(
            f"unparseable guarantee level: {raw!r} "
            f"(want G0-G4, 0-4, or one of {[m.name.lower() for m in cls]})"
        )


class AssumptionStatus(enum.Enum):
    """Is this assumption actually holding, and how would we know?

    This is the lever the whole gate turns on. An assumption is not "true" or "false" —
    it is *checked*, *watched*, or *hoped for*, and those three deserve different trust.

    - ``DISCHARGED`` — verified to hold in the deployed loop (a proof, an exhaustive check,
      a hardware interlock). Nothing further to watch.
    - ``MONITORED``  — not proven, but a runtime check exists that *fires* when it breaks,
      and something happens when it fires. A monitor with no fallback is not a monitor.
    - ``ASSUMED``    — believed, unverified, unwatched. Silence here is the dangerous case:
      when this breaks, you find out from the incident report.
    - ``VIOLATED``   — known not to hold. Honest, and fatal to the claim.
    """

    DISCHARGED = "discharged"
    MONITORED = "monitored"
    ASSUMED = "assumed"
    VIOLATED = "violated"

    @property
    def ceiling(self) -> GuaranteeLevel:
        """The strongest guarantee this assumption status can support.

        This mapping *is* the repo's central design judgment, so it is written once, here:

        - A ``VIOLATED`` assumption caps everything at G0. A demo is all you have left.
        - An ``ASSUMED`` one caps at **G1 (empirical)**. You may report what you measured;
          you may not promise what will happen, because the thing your promise rests on is
          unchecked. This is the rule that catches "we used an MPC, therefore it is safe."
        - A ``MONITORED`` one caps at **G3 (robust)**. A live check plus a fallback earns you
          robustness — but not certification, because you are detecting the violation rather
          than having excluded it.
        - A ``DISCHARGED`` one caps at G4. It is not in the way.
        """
        return {
            AssumptionStatus.VIOLATED: GuaranteeLevel.ANECDOTE,
            AssumptionStatus.ASSUMED: GuaranteeLevel.EMPIRICAL,
            AssumptionStatus.MONITORED: GuaranteeLevel.ROBUST,
            AssumptionStatus.DISCHARGED: GuaranteeLevel.CERTIFIED,
        }[self]

    @classmethod
    def parse(cls, raw: Any) -> "AssumptionStatus":
        if isinstance(raw, cls):
            return raw
        if isinstance(raw, str):
            token = raw.strip().lower()
            by_value = {m.value: m for m in cls}
            if token in by_value:
                return by_value[token]
        raise SpineError(
            f"unparseable assumption status: {raw!r} (want one of {[m.value for m in cls]})"
        )


class EvidenceType(enum.Enum):
    """Where a claim's support came from. Engagement is not evidence.

    Borrowed from research-anything's taxonomy and specialised for control: the weak kinds
    cannot carry a strong guarantee no matter how confidently they are written.
    """

    PROOF = "proof"                    # machine-checked or peer-reviewed formal argument
    HARDWARE = "hardware"              # measured on the real plant
    SIMULATION = "simulation"          # measured in sim; sim2real gap unpriced
    BENCHMARK = "benchmark"            # a standard dataset/task
    ABLATION = "ablation"              # controlled comparison
    ANALOGY = "analogy"                # a structural metaphor, not a measurement
    CLAIM = "claim"                    # asserted in a paper/blog, not independently checked

    @property
    def ceiling(self) -> GuaranteeLevel:
        """The strongest guarantee this *kind* of evidence can support on its own."""
        return {
            EvidenceType.PROOF: GuaranteeLevel.CERTIFIED,
            EvidenceType.HARDWARE: GuaranteeLevel.ROBUST,
            EvidenceType.SIMULATION: GuaranteeLevel.STATISTICAL,
            EvidenceType.BENCHMARK: GuaranteeLevel.EMPIRICAL,
            EvidenceType.ABLATION: GuaranteeLevel.EMPIRICAL,
            EvidenceType.ANALOGY: GuaranteeLevel.ANECDOTE,
            EvidenceType.CLAIM: GuaranteeLevel.ANECDOTE,
        }[self]

    @classmethod
    def parse(cls, raw: Any) -> "EvidenceType":
        if isinstance(raw, cls):
            return raw
        if isinstance(raw, str):
            by_value = {m.value: m for m in cls}
            token = raw.strip().lower()
            if token in by_value:
                return by_value[token]
        raise SpineError(
            f"unparseable evidence type: {raw!r} (want one of {[m.value for m in cls]})"
        )


# --------------------------------------------------------------------------------------
# The six organs
# --------------------------------------------------------------------------------------


class Organ(enum.Enum):
    """The six organs every feedback loop has, named so they can be matched across domains.

    A thermostat and a humanoid robot and an LLM agent differ in *what fills* each slot,
    never in *which slots exist*. That invariance is what makes cross-domain transfer of
    control results possible at all — and it is why this enum is a closed set.
    """

    REFERENCE = "reference"    # what you want:      setpoint, prompt, goal pose, target dist
    COMPARATOR = "comparator"  # how you see the gap: error signal, loss, reward, advantage
    CONTROLLER = "controller"  # what decides:       PID, MPC solve, policy net, sampler
    ACTUATOR = "actuator"      # what acts:          motor torque, emitted token, API call
    PLANT = "plant"            # what is acted on:   rigid body, the world, the user, the GPU
    SENSOR = "sensor"          # what reports back:  encoder, IMU, eval, reward model, log

    @property
    def plain(self) -> str:
        """The thermostat's version of this organ."""
        return {
            "reference": "the temperature you asked for",
            "comparator": "the gap between asked-for and actual",
            "controller": "the decision to fire the furnace",
            "actuator": "the furnace itself",
            "plant": "the room",
            "sensor": "the thermometer",
        }[self.value]

    @classmethod
    def parse(cls, raw: Any) -> "Organ":
        if isinstance(raw, cls):
            return raw
        if isinstance(raw, str):
            by_value = {m.value: m for m in cls}
            token = raw.strip().lower()
            if token in by_value:
                return by_value[token]
        raise SpineError(f"unknown organ: {raw!r} (want one of {[m.value for m in cls]})")


# --------------------------------------------------------------------------------------
# Assumption
# --------------------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Assumption:
    """One thing that must hold for a guarantee to mean anything.

    ``statement`` is prose a human reads; ``status`` is what the gate arithmetic uses;
    ``check`` names the concrete mechanism when there is one (a monitor, a proof, an
    interlock). The invariant enforced here is small but load-bearing: **you may not mark
    an assumption monitored or discharged without naming how.** An unnamed check is a
    wish, and wishes were exactly what the gate exists to catch.
    """

    id: str
    statement: str
    status: AssumptionStatus
    check: str | None = None          # how it is monitored/discharged (required for those)
    breaks_when: str | None = None    # the condition under which it stops holding
    source: str | None = None         # where this assumption was found/stated

    def __post_init__(self) -> None:
        if not self.id or not self.id.strip():
            raise SpineError("assumption needs a non-empty id")
        if not self.statement or not self.statement.strip():
            raise SpineError(f"assumption {self.id!r} needs a non-empty statement")
        needs_check = {AssumptionStatus.MONITORED, AssumptionStatus.DISCHARGED}
        if self.status in needs_check and not (self.check and self.check.strip()):
            raise SpineError(
                f"assumption {self.id!r} is marked {self.status.value!r} but names no check. "
                "An unnamed check is a wish: give `check:` the monitor, proof, or interlock, "
                "or downgrade the status to 'assumed'."
            )

    @property
    def ceiling(self) -> GuaranteeLevel:
        """Strongest guarantee this assumption permits."""
        return self.status.ceiling

    @property
    def is_load_bearing(self) -> bool:
        """True when this assumption is the kind that silently caps a claim.

        ``ASSUMED`` and ``VIOLATED`` are the two statuses that pull a guarantee down, so
        these are the rows a reviewer should read first.
        """
        return self.status in {AssumptionStatus.ASSUMED, AssumptionStatus.VIOLATED}

    @classmethod
    def from_dict(cls, raw: Mapping[str, Any]) -> "Assumption":
        if not isinstance(raw, Mapping):
            raise SpineError(f"assumption must be a mapping, got {type(raw).__name__}")
        unknown = set(raw) - {
            "id", "statement", "status", "check", "breaks_when", "source",
        }
        if unknown:
            raise SpineError(f"assumption has unknown keys: {sorted(unknown)}")
        try:
            return cls(
                id=str(raw["id"]).strip(),
                statement=str(raw["statement"]).strip(),
                status=AssumptionStatus.parse(raw["status"]),
                check=_opt_str(raw.get("check")),
                breaks_when=_opt_str(raw.get("breaks_when")),
                source=_opt_str(raw.get("source")),
            )
        except KeyError as exc:
            raise SpineError(f"assumption missing required key: {exc}") from exc


# --------------------------------------------------------------------------------------
# LoopCard — the six organs, filled in
# --------------------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class LoopCard:
    """A concrete system mapped onto the six organs, plus the three fields people forget.

    The three forgotten fields are where real systems actually fail:

    - ``latency`` — every loop has a delay, and delay is what turns a stable controller
      unstable. A loop whose delay is unstated is a loop nobody has analysed.
    - ``authority`` — what the controller is *allowed* to do. The 737 MAX's MCAS had more
      authority than its designers modelled; that sentence is the whole accident.
    - ``fallback`` — what happens when the loop fails. "Nothing" is a valid, and damning,
      answer.
    """

    id: str
    system: str                     # the concrete system, not a category
    domain: str                     # foreign key into data/domains.yml
    organs: Mapping[Organ, str]     # every organ -> the real handle filling it
    latency: str | None = None
    authority: str | None = None
    fallback: str | None = None
    notes: str | None = None

    def __post_init__(self) -> None:
        if not self.id or not self.id.strip():
            raise SpineError("loop card needs a non-empty id")
        missing = [o.value for o in Organ if o not in self.organs]
        if missing:
            raise SpineError(
                f"loop card {self.id!r} is incomplete — missing organs: {missing}. "
                "If you cannot name the sensor, it is not a control problem."
            )
        blank = sorted(o.value for o, v in self.organs.items() if not str(v).strip())
        if blank:
            raise SpineError(f"loop card {self.id!r} has blank organs: {blank}")

    @property
    def is_complete(self) -> bool:
        """All six organs named *and* the three failure-mode fields filled in.

        Construction already guarantees the six organs, so this reports on the fields that
        separate a diagram from an analysis.
        """
        return all(
            f is not None and str(f).strip()
            for f in (self.latency, self.authority, self.fallback)
        )

    @property
    def gaps(self) -> list[str]:
        """Which of the three analysis fields are still missing. Empty means complete."""
        return [
            name
            for name, value in (
                ("latency", self.latency),
                ("authority", self.authority),
                ("fallback", self.fallback),
            )
            if not (value is not None and str(value).strip())
        ]

    def organ(self, which: Organ | str) -> str:
        """Look up one organ by enum or by name."""
        return self.organs[Organ.parse(which)]

    @classmethod
    def from_dict(cls, raw: Mapping[str, Any]) -> "LoopCard":
        if not isinstance(raw, Mapping):
            raise SpineError(f"loop card must be a mapping, got {type(raw).__name__}")
        unknown = set(raw) - {
            "id", "system", "domain", "organs",
            "latency", "authority", "fallback", "notes",
        }
        if unknown:
            raise SpineError(f"loop card has unknown keys: {sorted(unknown)}")
        try:
            organs_raw = raw["organs"]
            if not isinstance(organs_raw, Mapping):
                raise SpineError(
                    f"loop card {raw.get('id')!r}: `organs` must be a mapping of organ -> handle"
                )
            organs = {Organ.parse(k): str(v).strip() for k, v in organs_raw.items()}
            return cls(
                id=str(raw["id"]).strip(),
                system=str(raw["system"]).strip(),
                domain=str(raw["domain"]).strip(),
                organs=organs,
                latency=_opt_str(raw.get("latency")),
                authority=_opt_str(raw.get("authority")),
                fallback=_opt_str(raw.get("fallback")),
                notes=_opt_str(raw.get("notes")),
            )
        except KeyError as exc:
            raise SpineError(f"loop card missing required key: {exc}") from exc


# --------------------------------------------------------------------------------------
# Claim
# --------------------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Claim:
    """An assertion that some loop achieves some guarantee — the unit the gate judges.

    A claim is *not* trusted as written. ``claimed`` is what its author says; the gate
    computes what it has actually earned. The difference between those two numbers is the
    single most useful output of this repo.
    """

    id: str
    statement: str
    claimed: GuaranteeLevel
    evidence: Sequence[EvidenceType] = field(default_factory=tuple)
    assumptions: Sequence[Assumption] = field(default_factory=tuple)
    loop: str | None = None          # foreign key into loop cards
    domain: str | None = None
    concepts: Sequence[str] = field(default_factory=tuple)  # concept ids this claim is about
    source: str | None = None        # citation / url
    verified: bool = False           # was the source resolved against a primary?
    bridge: str | None = None        # 'rigorous' | 'analogy' for control<->AI mappings
    notes: str | None = None

    def __post_init__(self) -> None:
        if not self.id or not self.id.strip():
            raise SpineError("claim needs a non-empty id")
        if not self.statement or not self.statement.strip():
            raise SpineError(f"claim {self.id!r} needs a non-empty statement")
        if self.bridge is not None and self.bridge not in {"rigorous", "analogy"}:
            raise SpineError(
                f"claim {self.id!r}: bridge must be 'rigorous' or 'analogy', got {self.bridge!r}. "
                "Conflating a theorem with a metaphor is the failure this field exists to stop."
            )
        seen: set[str] = set()
        for a in self.assumptions:
            if a.id in seen:
                raise SpineError(f"claim {self.id!r} has duplicate assumption id {a.id!r}")
            seen.add(a.id)

    @property
    def weakest_assumption(self) -> Assumption | None:
        """The assumption that caps this claim. ``None`` when there are no assumptions.

        Ties are broken deterministically by id so output is byte-stable across runs —
        a hard requirement for drift-gating generated docs.
        """
        if not self.assumptions:
            return None
        return min(self.assumptions, key=lambda a: (int(a.ceiling), a.id))

    @classmethod
    def from_dict(cls, raw: Mapping[str, Any]) -> "Claim":
        if not isinstance(raw, Mapping):
            raise SpineError(f"claim must be a mapping, got {type(raw).__name__}")
        unknown = set(raw) - {
            "id", "statement", "claimed", "evidence", "assumptions",
            "loop", "domain", "concepts", "source", "verified", "bridge", "notes",
        }
        if unknown:
            raise SpineError(f"claim has unknown keys: {sorted(unknown)}")
        try:
            return cls(
                id=str(raw["id"]).strip(),
                statement=str(raw["statement"]).strip(),
                claimed=GuaranteeLevel.parse(raw["claimed"]),
                evidence=tuple(EvidenceType.parse(e) for e in raw.get("evidence", ())),
                assumptions=tuple(
                    Assumption.from_dict(a) for a in raw.get("assumptions", ())
                ),
                loop=_opt_str(raw.get("loop")),
                domain=_opt_str(raw.get("domain")),
                concepts=tuple(str(c).strip() for c in raw.get("concepts", ())),
                source=_opt_str(raw.get("source")),
                verified=bool(raw.get("verified", False)),
                bridge=_opt_str(raw.get("bridge")),
                notes=_opt_str(raw.get("notes")),
            )
        except KeyError as exc:
            raise SpineError(f"claim missing required key: {exc}") from exc


# --------------------------------------------------------------------------------------
# Graph primitives
# --------------------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Node:
    """A typed knowledge-graph node.

    Kept deliberately thin: the graph carries structure, the spine files carry content.
    """

    id: str
    kind: str          # concept | person | work | lab | question | application | domain | organ
    label: str
    attrs: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.id or not self.id.strip():
            raise SpineError("node needs a non-empty id")
        if self.kind not in NODE_KINDS:
            raise SpineError(
                f"node {self.id!r} has unknown kind {self.kind!r} (want one of {sorted(NODE_KINDS)})"
            )


@dataclass(frozen=True, slots=True)
class Edge:
    """A typed directed edge."""

    src: str
    dst: str
    rel: str

    def __post_init__(self) -> None:
        if self.rel not in EDGE_RELS:
            raise SpineError(
                f"edge {self.src}->{self.dst} has unknown relation {self.rel!r} "
                f"(want one of {sorted(EDGE_RELS)})"
            )


NODE_KINDS: frozenset[str] = frozenset(
    {"concept", "person", "work", "lab", "question", "application", "domain", "organ", "claim"}
)
"""Closed set of node kinds. Adding one is a deliberate schema change, not a typo."""

EDGE_RELS: frozenset[str] = frozenset(
    {
        "authored",      # person  -> work
        "affiliated",    # person  -> lab
        "introduces",    # work    -> concept
        "applies",       # application -> concept
        "in_domain",     # application|question|claim -> domain
        "maps_to",       # concept -> organ
        "asks",          # question -> concept
        "supports",      # work    -> claim
        "about",         # claim   -> concept
        "uses",          # domain  -> concept
        "owns",          # person  -> concept  (the one idea they are known for)
        "advised",       # person  -> person   (doctoral lineage)
        "successor",     # concept -> concept  (this refines/replaces that)
    }
)
"""Closed set of relations. The graph's invariants are stated in terms of these."""


# --------------------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------------------


def _opt_str(value: Any) -> str | None:
    """Normalise an optional scalar to a stripped string or ``None``.

    Empty and whitespace-only strings become ``None`` so that "present but blank" and
    "absent" are the same thing everywhere downstream — otherwise ``is_complete`` would
    happily accept ``latency: ""``.
    """
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def dedupe_ids(items: Iterable[Any], what: str) -> None:
    """Raise ``SpineError`` when ``items`` contain a duplicate ``.id``."""
    seen: set[str] = set()
    for item in items:
        ident = getattr(item, "id", None)
        if ident in seen:
            raise SpineError(f"duplicate {what} id: {ident!r}")
        seen.add(ident)
