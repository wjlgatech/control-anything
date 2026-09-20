"""Registry — load the spine (``data/*.yml``) into typed objects, once.

``data/*.yml`` is the single source of truth. Every published surface (README tables, the
knowledge graph, the skills) is *generated* from here and drift-gated. Nothing downstream
is hand-edited; if a table and the spine disagree, the spine wins and ``make check`` fails.

The registry is the only module that touches the filesystem, so everything else in ``core``
stays a pure function of its inputs and therefore trivially testable.
"""

from __future__ import annotations

import functools
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping, Sequence

import yaml

from .models import Claim, LoopCard, SpineError, dedupe_ids

__all__ = ["Registry", "Spine", "repo_root", "data_dir"]


@functools.lru_cache(maxsize=1)
def repo_root() -> Path:
    """Locate the repo root by walking up to the directory holding ``data/``.

    Walking up beats a hardcoded relative path: the same code then works from ``scripts/``,
    from ``tests/``, and from an installed package during development.
    """
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "data").is_dir() and (parent / "pyproject.toml").is_file():
            return parent
    # Fall back to three levels up: src/control_anything/core/registry.py -> repo root
    return here.parents[3]


def data_dir() -> Path:
    """Absolute path to the spine directory."""
    return repo_root() / "data"


def _load_yaml(path: Path) -> Any:
    """Read one YAML file, with a clear error when it is missing or malformed."""
    if not path.is_file():
        raise SpineError(f"spine file not found: {path}")
    try:
        with path.open("r", encoding="utf-8") as handle:
            return yaml.safe_load(handle)
    except yaml.YAMLError as exc:
        raise SpineError(f"malformed YAML in {path.name}: {exc}") from exc


def _expect_list(raw: Any, path: Path, key: str) -> list[Any]:
    """Pull ``key`` from a top-level mapping and insist it is a list."""
    if raw is None:
        return []
    if not isinstance(raw, Mapping):
        raise SpineError(f"{path.name}: top level must be a mapping with a {key!r} key")
    items = raw.get(key)
    if items is None:
        return []
    if not isinstance(items, list):
        raise SpineError(f"{path.name}: {key!r} must be a list, got {type(items).__name__}")
    return items


@dataclass(frozen=True, slots=True)
class Spine:
    """Everything loaded from ``data/``, already validated into typed objects."""

    domains: Sequence[Mapping[str, Any]] = field(default_factory=tuple)
    concepts: Sequence[Mapping[str, Any]] = field(default_factory=tuple)
    people: Sequence[Mapping[str, Any]] = field(default_factory=tuple)
    works: Sequence[Mapping[str, Any]] = field(default_factory=tuple)
    labs: Sequence[Mapping[str, Any]] = field(default_factory=tuple)
    questions: Sequence[Mapping[str, Any]] = field(default_factory=tuple)
    applications: Sequence[Mapping[str, Any]] = field(default_factory=tuple)
    loops: Sequence[LoopCard] = field(default_factory=tuple)
    claims: Sequence[Claim] = field(default_factory=tuple)

    def domain_ids(self) -> set[str]:
        return {str(d["id"]) for d in self.domains}

    def concept_ids(self) -> set[str]:
        return {str(c["id"]) for c in self.concepts}

    def loop_ids(self) -> set[str]:
        return {loop.id for loop in self.loops}


class Registry:
    """Load and validate the spine.

    :param root: repo root; defaults to auto-detection so callers rarely pass it.
    """

    #: filename -> top-level list key, for the plain (untyped) spine files
    PLAIN_FILES: Mapping[str, str] = {
        "domains.yml": "domains",
        "concepts.yml": "concepts",
        "people.yml": "people",
        "works.yml": "works",
        "labs.yml": "labs",
        "questions.yml": "questions",
        "applications.yml": "applications",
    }

    def __init__(self, root: Path | None = None) -> None:
        self.root = Path(root) if root is not None else repo_root()
        self.data = self.root / "data"

    def load(self) -> Spine:
        """Read every spine file, validate, and return typed objects.

        Raises ``SpineError`` with a file-and-id-specific message on the first problem —
        a gate whose failure message does not say *which row* is wrong is a gate people
        learn to ignore.
        """
        plain: dict[str, list[Mapping[str, Any]]] = {}
        for filename, key in self.PLAIN_FILES.items():
            path = self.data / filename
            items = _expect_list(_load_yaml(path), path, key)
            for item in items:
                if not isinstance(item, Mapping) or "id" not in item:
                    raise SpineError(f"{filename}: every {key[:-1]} needs an `id` -> {item!r}")
            ids = [str(i["id"]) for i in items]
            if len(ids) != len(set(ids)):
                dupes = sorted({i for i in ids if ids.count(i) > 1})
                raise SpineError(f"{filename}: duplicate ids {dupes}")
            plain[key] = items

        loops = self._load_loops()
        claims = self._load_claims()
        dedupe_ids(loops, "loop card")
        dedupe_ids(claims, "claim")

        spine = Spine(
            domains=tuple(plain["domains"]),
            concepts=tuple(plain["concepts"]),
            people=tuple(plain["people"]),
            works=tuple(plain["works"]),
            labs=tuple(plain["labs"]),
            questions=tuple(plain["questions"]),
            applications=tuple(plain["applications"]),
            loops=tuple(loops),
            claims=tuple(claims),
        )
        self._check_foreign_keys(spine)
        return spine

    def _load_loops(self) -> list[LoopCard]:
        path = self.data / "loops.yml"
        raw = _expect_list(_load_yaml(path), path, "loops")
        out: list[LoopCard] = []
        for item in raw:
            try:
                out.append(LoopCard.from_dict(item))
            except SpineError as exc:
                raise SpineError(f"loops.yml: {exc}") from exc
        return out

    def _load_claims(self) -> list[Claim]:
        path = self.data / "claims.yml"
        raw = _expect_list(_load_yaml(path), path, "claims")
        out: list[Claim] = []
        for item in raw:
            try:
                out.append(Claim.from_dict(item))
            except SpineError as exc:
                raise SpineError(f"claims.yml: {exc}") from exc
        return out

    @staticmethod
    def _check_foreign_keys(spine: Spine) -> None:
        """Every cross-file reference must resolve. A dangling id is a silent lie."""
        domains = spine.domain_ids()
        concepts = spine.concept_ids()
        loops = spine.loop_ids()

        for loop in spine.loops:
            if loop.domain not in domains:
                raise SpineError(
                    f"loops.yml: loop {loop.id!r} references unknown domain {loop.domain!r}"
                )

        for claim in spine.claims:
            if claim.domain is not None and claim.domain not in domains:
                raise SpineError(
                    f"claims.yml: claim {claim.id!r} references unknown domain {claim.domain!r}"
                )
            if claim.loop is not None and claim.loop not in loops:
                raise SpineError(
                    f"claims.yml: claim {claim.id!r} references unknown loop {claim.loop!r}"
                )
            for cid in claim.concepts:
                if cid not in concepts:
                    raise SpineError(
                        f"claims.yml: claim {claim.id!r} references unknown concept {cid!r}"
                    )

        for work in spine.works:
            for cid in work.get("concepts", ()) or ():
                if str(cid) not in concepts:
                    raise SpineError(
                        f"works.yml: work {work['id']!r} references unknown concept {cid!r}"
                    )

        people_ids = {str(p["id"]) for p in spine.people}
        for work in spine.works:
            for pid in work.get("authors", ()) or ():
                if str(pid) not in people_ids:
                    raise SpineError(
                        f"works.yml: work {work['id']!r} references unknown person {pid!r}"
                    )

        lab_ids = {str(l["id"]) for l in spine.labs}
        for person in spine.people:
            for lid in person.get("labs", ()) or ():
                if str(lid) not in lab_ids:
                    raise SpineError(
                        f"people.yml: person {person['id']!r} references unknown lab {lid!r}"
                    )
            for aid in person.get("advised_by", ()) or ():
                if str(aid) not in people_ids:
                    raise SpineError(
                        f"people.yml: person {person['id']!r} references unknown advisor {aid!r}"
                    )

        for question in spine.questions:
            if str(question.get("domain", "")) not in domains:
                raise SpineError(
                    f"questions.yml: question {question['id']!r} references unknown domain "
                    f"{question.get('domain')!r}"
                )

        for app in spine.applications:
            if str(app.get("domain", "")) not in domains:
                raise SpineError(
                    f"applications.yml: application {app['id']!r} references unknown domain "
                    f"{app.get('domain')!r}"
                )
