"""Citations as checkable handles — the offline half of "was this source resolved?".

``verified: true`` used to be a flag a human typed. A typed flag is a wish, which is the
exact thing ``ControlClaimGate`` exists to catch in everyone else's claims. So a claim now
earns ``verified`` only when every handle in its ``source`` (an arXiv id, a DOI, a URL, an
ISBN) has a row in ``data/resolutions.yml`` recording what the primary source actually
returned — its title, the service that answered, and the date.

This module is pure and offline: it *extracts* handles and *checks* them against the
recorded resolutions. The network half — actually asking arXiv / Crossref / the web — is
``scripts/resolve.py``, kept outside core so ``make check`` never touches the network.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Iterable, Mapping

_ARXIV = re.compile(r"arXiv:(\d{4}\.\d{4,5})", re.IGNORECASE)
_DOI = re.compile(r"\b(10\.\d{4,9}/[^\s;,\"']+)")
_URL = re.compile(r"(https?://[^\s;,\"']+)")
_ISBN = re.compile(r"ISBN[:\s]*([0-9Xx-]{10,17})")


def extract_refs(source: str | None) -> list[str]:
    """Every checkable handle in a free-text ``source``, normalised, in order, deduped.

    Handles come out as ``arXiv:NNNN.NNNNN`` · ``doi:10.x/…`` · ``url:https://…`` ·
    ``isbn:NNNNNNNNNN``. Prose with no handle ("standard textbook result") yields ``[]`` —
    which is precisely what makes such a claim unverifiable.
    """
    if not source:
        return []
    refs: list[str] = []
    text = source
    for url in _URL.findall(text):
        refs.append(f"url:{url.rstrip('.)')}")
    text = _URL.sub(" ", text)  # a DOI inside a URL is the URL's, not a second handle
    refs += [f"arXiv:{m}" for m in _ARXIV.findall(text)]
    refs += [f"doi:{m.rstrip('.)').lower()}" for m in _DOI.findall(text)]
    refs += [f"isbn:{m.replace('-', '').upper()}" for m in _ISBN.findall(text)]
    return list(dict.fromkeys(refs))


def work_source(work: Mapping[str, Any]) -> str:
    """A work's handles as one source string — works carry doi/arxiv/url as separate keys."""
    parts = [str(work.get("source") or "")]
    if work.get("doi"):
        parts.append(str(work["doi"]))
    if work.get("arxiv"):
        parts.append(f"arXiv:{work['arxiv']}")
    if work.get("url"):
        parts.append(str(work["url"]))
    return " ; ".join(p for p in parts if p)


@dataclass(frozen=True, slots=True)
class Resolution:
    """What a primary source returned when we asked it."""

    ref: str
    title: str
    via: str
    checked: str

    @classmethod
    def from_raw(cls, raw: Mapping[str, Any]) -> "Resolution":
        return cls(
            ref=str(raw["ref"]),
            title=str(raw.get("title") or "").strip(),
            via=str(raw.get("via") or "").strip(),
            checked=str(raw.get("checked") or "").strip(),
        )


def index_resolutions(rows: Iterable[Mapping[str, Any]]) -> dict[str, Resolution]:
    """``ref -> Resolution``, keeping only rows that actually carry a title and a service."""
    out: dict[str, Resolution] = {}
    for raw in rows:
        res = Resolution.from_raw(raw)
        if res.title and res.via:
            out[res.ref] = res
    return out


def verification_problems(
    items: Iterable[tuple[str, str | None, bool]],
    resolutions: Mapping[str, Resolution],
) -> list[str]:
    """Why each ``verified: true`` item has not earned it. Empty list = every flag is earned.

    ``items`` are ``(id, source, verified)``. A verified item must name at least one handle,
    and every handle it names must be resolved — a half-resolved source is not resolved.
    """
    problems: list[str] = []
    for item_id, source, verified in items:
        if not verified:
            continue
        refs = extract_refs(source)
        if not refs:
            problems.append(
                f"{item_id!r} is verified: true but its source {source!r} names no "
                "checkable handle (arXiv / DOI / URL / ISBN)"
            )
            continue
        missing = [r for r in refs if r not in resolutions]
        if missing:
            problems.append(
                f"{item_id!r} is verified: true but {missing} has no row in "
                "data/resolutions.yml — run `make resolve`"
            )
    return problems
