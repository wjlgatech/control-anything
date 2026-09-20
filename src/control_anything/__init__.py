"""control-anything — control theory as an instrument for judging AI systems.

The public surface is deliberately small: the gate, the models it judges, and the graph
that connects them. Everything else is an implementation detail behind ``core``/``addons``.
"""

from .core.claim_gate import ControlClaimGate, GateStats, Verdict
from .core.graph import KnowledgeGraph, build_graph
from .core.models import (
    Assumption,
    AssumptionStatus,
    Claim,
    EvidenceType,
    GuaranteeLevel,
    LoopCard,
    Organ,
    SpineError,
)
from .core.registry import Registry, Spine

__version__ = "0.1.0"

__all__ = [
    "Assumption",
    "AssumptionStatus",
    "Claim",
    "ControlClaimGate",
    "EvidenceType",
    "GateStats",
    "GuaranteeLevel",
    "KnowledgeGraph",
    "LoopCard",
    "Organ",
    "Registry",
    "Spine",
    "SpineError",
    "Verdict",
    "build_graph",
    "__version__",
]
