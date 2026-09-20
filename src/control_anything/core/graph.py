"""KnowledgeGraph — the knowledge base as a typed graph, with invariants CI can enforce.

Why a graph and not a list. A list answers *"what do we know about MPC?"*. A graph answers
*"which assumption is load-bearing for this claim, who first stated it, in what paper, and
which other domain already learned it the hard way?"* — and that second question is the one
worth building a repo for.

Three invariants are gated in CI, and each catches a different class of rot:

1. **No orphans.** Every node connects to something. An orphan is a fact nobody can reach,
   which is a fact nobody will maintain.
2. **Gate coverage is total.** Every ``claim`` node reaches a ``domain``, so no claim can
   reach output without being judged. This catches a wiring bug no unit test would.
3. **Every concept maps to an organ.** If a control concept cannot be placed on the six-organ
   loop, either the concept is out of scope or the ontology is wrong. Both are worth knowing.

Pure stdlib — breadth-first search over adjacency dicts. Keeping the core free of networkx
is what lets ``make check`` run on a bare machine.
"""

from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass
from typing import Iterable, Iterator, Mapping, Sequence

from .models import Edge, Node, Organ
from .registry import Spine

__all__ = ["KnowledgeGraph", "GraphReport", "build_graph"]


@dataclass(frozen=True, slots=True)
class GraphReport:
    """The result of checking every invariant. ``ok`` is what the exit code keys off."""

    nodes: int
    edges: int
    orphans: Sequence[str]
    unmapped_concepts: Sequence[str]
    ungated_claims: Sequence[str]
    kind_counts: Mapping[str, int]

    @property
    def gate_coverage(self) -> float:
        """Fraction of claims that reach a domain (and therefore the gate).

        ``1.0`` for an empty corpus: vacuously total, and it keeps the metric monotone
        as the corpus grows from nothing.
        """
        claims = self.kind_counts.get("claim", 0)
        if claims == 0:
            return 1.0
        return round((claims - len(self.ungated_claims)) / claims, 4)

    @property
    def ok(self) -> bool:
        return not (self.orphans or self.unmapped_concepts or self.ungated_claims)

    def failures(self) -> list[str]:
        """Human-readable failures, empty when green."""
        out: list[str] = []
        if self.orphans:
            out.append(
                f"{len(self.orphans)} orphan node(s) with no edges: {list(self.orphans)[:8]}"
            )
        if self.unmapped_concepts:
            out.append(
                f"{len(self.unmapped_concepts)} concept(s) not mapped to a loop organ: "
                f"{list(self.unmapped_concepts)[:8]}"
            )
        if self.ungated_claims:
            out.append(
                f"{len(self.ungated_claims)} claim(s) that never reach a domain: "
                f"{list(self.ungated_claims)[:8]}"
            )
        return out


class KnowledgeGraph:
    """A typed directed graph over the spine, with reachability queries."""

    def __init__(self, nodes: Iterable[Node], edges: Iterable[Edge]) -> None:
        self._nodes: dict[str, Node] = {n.id: n for n in nodes}
        self._edges: list[Edge] = list(edges)
        self._out: dict[str, list[Edge]] = defaultdict(list)
        self._in: dict[str, list[Edge]] = defaultdict(list)
        for edge in self._edges:
            self._out[edge.src].append(edge)
            self._in[edge.dst].append(edge)

    # -- accessors ---------------------------------------------------------------------

    def __len__(self) -> int:
        return len(self._nodes)

    @property
    def edges(self) -> Sequence[Edge]:
        return tuple(self._edges)

    def node(self, node_id: str) -> Node | None:
        return self._nodes.get(node_id)

    def nodes_of_kind(self, kind: str) -> list[Node]:
        """All nodes of one kind, sorted by id for deterministic output."""
        return sorted(
            (n for n in self._nodes.values() if n.kind == kind), key=lambda n: n.id
        )

    def degree(self, node_id: str) -> int:
        return len(self._out[node_id]) + len(self._in[node_id])

    def neighbours(self, node_id: str, *, rel: str | None = None) -> list[str]:
        """Direct successors, optionally filtered by relation."""
        return sorted(
            e.dst for e in self._out[node_id] if rel is None or e.rel == rel
        )

    # -- reachability ------------------------------------------------------------------

    def reachable(
        self,
        start: str,
        *,
        kinds: frozenset[str] | set[str] | None = None,
        max_hops: int | None = None,
    ) -> set[str]:
        """Breadth-first set of nodes reachable from ``start``.

        :param kinds: when given, only nodes of these kinds are returned (traversal still
            passes *through* other kinds — we filter the answer, not the search).
        :param max_hops: optional depth bound.
        """
        seen: set[str] = {start}
        out: set[str] = set()
        queue: deque[tuple[str, int]] = deque([(start, 0)])
        while queue:
            current, depth = queue.popleft()
            if max_hops is not None and depth >= max_hops:
                continue
            for edge in self._out[current]:
                if edge.dst in seen:
                    continue
                seen.add(edge.dst)
                node = self._nodes.get(edge.dst)
                if node is not None and (kinds is None or node.kind in kinds):
                    out.add(edge.dst)
                queue.append((edge.dst, depth + 1))
        return out

    def trace(self, start: str, target_kind: str) -> list[list[str]]:
        """Shortest paths from ``start`` to every node of ``target_kind``.

        Powers ``ca.py trace``: walk from a claim to the concepts and works behind it, so a
        reviewer can see *why* an entry says what it says without reading the whole spine.
        """
        paths: list[list[str]] = []
        seen: set[str] = {start}
        queue: deque[list[str]] = deque([[start]])
        while queue:
            path = queue.popleft()
            node = self._nodes.get(path[-1])
            if node is not None and node.kind == target_kind and len(path) > 1:
                paths.append(path)
                continue
            for edge in self._out[path[-1]]:
                if edge.dst in seen:
                    continue
                seen.add(edge.dst)
                queue.append([*path, edge.dst])
        return sorted(paths, key=lambda p: (len(p), p))

    def walk(self) -> Iterator[Node]:
        """Every node, id-sorted."""
        yield from sorted(self._nodes.values(), key=lambda n: n.id)

    # -- invariants --------------------------------------------------------------------

    def check(self) -> GraphReport:
        """Run every invariant and report. Never raises — the caller picks the exit code."""
        orphans = sorted(nid for nid in self._nodes if self.degree(nid) == 0)

        organ_ids = {f"organ:{o.value}" for o in Organ}
        unmapped = sorted(
            n.id
            for n in self.nodes_of_kind("concept")
            if not (self.reachable(n.id, kinds={"organ"}) & organ_ids)
        )

        ungated = sorted(
            n.id
            for n in self.nodes_of_kind("claim")
            if not self.reachable(n.id, kinds={"domain"})
        )

        counts: dict[str, int] = defaultdict(int)
        for node in self._nodes.values():
            counts[node.kind] += 1

        return GraphReport(
            nodes=len(self._nodes),
            edges=len(self._edges),
            orphans=tuple(orphans),
            unmapped_concepts=tuple(unmapped),
            ungated_claims=tuple(ungated),
            kind_counts=dict(sorted(counts.items())),
        )


def build_graph(spine: Spine) -> KnowledgeGraph:
    """Assemble the knowledge graph from a loaded spine.

    Node ids are namespaced (``concept:lyapunov``, ``person:kalman``) so that a concept and
    a person may share a slug without colliding — which they do, constantly, in this field.
    """
    nodes: list[Node] = []
    edges: list[Edge] = []

    for organ in Organ:
        nodes.append(
            Node(
                id=f"organ:{organ.value}",
                kind="organ",
                label=organ.value,
                attrs={"plain": organ.plain},
            )
        )

    for domain in spine.domains:
        did = str(domain["id"])
        nodes.append(
            Node(id=f"domain:{did}", kind="domain", label=str(domain.get("name", did)),
                 attrs=dict(domain))
        )
        for cid in domain.get("concepts", ()) or ():
            edges.append(Edge(f"domain:{did}", f"concept:{cid}", "uses"))

    for concept in spine.concepts:
        cid = str(concept["id"])
        nodes.append(
            Node(id=f"concept:{cid}", kind="concept", label=str(concept.get("name", cid)),
                 attrs=dict(concept))
        )
        for organ in concept.get("organs", ()) or ():
            edges.append(Edge(f"concept:{cid}", f"organ:{organ}", "maps_to"))
        for other in concept.get("refines", ()) or ():
            edges.append(Edge(f"concept:{cid}", f"concept:{other}", "successor"))

    for lab in spine.labs:
        lid = str(lab["id"])
        nodes.append(
            Node(id=f"lab:{lid}", kind="lab", label=str(lab.get("name", lid)), attrs=dict(lab))
        )
        for did in lab.get("domains", ()) or ():
            edges.append(Edge(f"lab:{lid}", f"domain:{did}", "in_domain"))

    for person in spine.people:
        pid = str(person["id"])
        nodes.append(
            Node(id=f"person:{pid}", kind="person", label=str(person.get("name", pid)),
                 attrs=dict(person))
        )
        for lid in person.get("labs", ()) or ():
            edges.append(Edge(f"person:{pid}", f"lab:{lid}", "affiliated"))
        for aid in person.get("advised_by", ()) or ():
            edges.append(Edge(f"person:{aid}", f"person:{pid}", "advised"))
        if person.get("owns_concept"):
            edges.append(Edge(f"person:{pid}", f"concept:{person['owns_concept']}", "owns"))

    for work in spine.works:
        wid = str(work["id"])
        nodes.append(
            Node(id=f"work:{wid}", kind="work", label=str(work.get("title", wid)),
                 attrs=dict(work))
        )
        for pid in work.get("authors", ()) or ():
            edges.append(Edge(f"person:{pid}", f"work:{wid}", "authored"))
        for cid in work.get("concepts", ()) or ():
            edges.append(Edge(f"work:{wid}", f"concept:{cid}", "introduces"))

    for question in spine.questions:
        qid = str(question["id"])
        nodes.append(
            Node(id=f"question:{qid}", kind="question", label=str(question.get("question", qid)),
                 attrs=dict(question))
        )
        edges.append(Edge(f"question:{qid}", f"domain:{question['domain']}", "in_domain"))
        for cid in question.get("concepts", ()) or ():
            edges.append(Edge(f"question:{qid}", f"concept:{cid}", "asks"))

    for app in spine.applications:
        aid = str(app["id"])
        nodes.append(
            Node(id=f"application:{aid}", kind="application",
                 label=str(app.get("name", aid)), attrs=dict(app))
        )
        edges.append(Edge(f"application:{aid}", f"domain:{app['domain']}", "in_domain"))
        for cid in app.get("concepts", ()) or ():
            edges.append(Edge(f"application:{aid}", f"concept:{cid}", "applies"))

    for claim in spine.claims:
        nodes.append(
            Node(id=f"claim:{claim.id}", kind="claim", label=claim.statement,
                 attrs={"claimed": claim.claimed.code, "verified": claim.verified})
        )
        if claim.domain:
            edges.append(Edge(f"claim:{claim.id}", f"domain:{claim.domain}", "in_domain"))
        for cid in claim.concepts:
            edges.append(Edge(f"claim:{claim.id}", f"concept:{cid}", "about"))

    # Known ids, so we can drop edges pointing at nodes that were never declared.
    known = {n.id for n in nodes}
    edges = [e for e in edges if e.src in known and e.dst in known]

    return KnowledgeGraph(nodes, edges)
