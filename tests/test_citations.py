"""Verification must be earned: a `verified: true` with no recorded resolution fails.

The offline half of citation checking. `scripts/resolve.py` asks primary services and
records what they said; these tests pin that a flag with nothing behind it cannot pass,
and that the real spine carries no such flag.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import yaml

from control_anything.core.citations import (
    extract_refs,
    index_resolutions,
    verification_problems,
    work_source,
)
from control_anything.core.registry import Registry

ROOT = Path(__file__).resolve().parents[1]
RES = {"arXiv:2211.17192": {"ref": "arXiv:2211.17192", "title": "Fast Inference", "via": "export.arxiv.org", "checked": "2026-09-24"}}


def test_extract_every_handle_kind_normalised_and_deduped():
    src = "arXiv:2211.17192; 10.1056/NEJMoa1907863; https://x.org/a.pdf ISBN 0-07-035958-X arXiv:2211.17192"
    assert extract_refs(src) == [
        "url:https://x.org/a.pdf", "arXiv:2211.17192", "doi:10.1056/nejmoa1907863", "isbn:007035958X",
    ]


def test_prose_has_no_handle():
    assert extract_refs("Classical power-system control; standard textbook result") == []
    assert extract_refs(None) == []


def test_doi_inside_url_is_not_a_second_handle():
    assert extract_refs("https://doi.org/10.1000/xyz") == ["url:https://doi.org/10.1000/xyz"]


def test_work_source_joins_separate_keys():
    assert extract_refs(work_source({"doi": "10.1000/a", "arxiv": "1234.5678"})) == ["arXiv:1234.5678", "doi:10.1000/a"]


def test_verified_prose_source_is_refused():
    problems = verification_problems([("c", "standard textbook result", True)], {})
    assert len(problems) == 1 and "no checkable handle" in problems[0]


def test_verified_unresolved_handle_is_refused_and_resolved_passes():
    idx = index_resolutions(RES.values())
    assert verification_problems([("c", "arXiv:2211.17192", True)], idx) == []
    assert "has no row" in verification_problems([("c", "arXiv:9999.99999", True)], idx)[0]


def test_half_resolved_source_is_not_resolved():
    idx = index_resolutions(RES.values())
    assert verification_problems([("c", "arXiv:2211.17192; arXiv:9999.99999", True)], idx)


def test_unverified_items_are_never_problems():
    assert verification_problems([("c", "anything", False)], {}) == []


def test_a_row_without_title_does_not_count():
    idx = index_resolutions([{"ref": "arXiv:1", "title": "", "via": "export.arxiv.org"}])
    assert idx == {}


def test_real_spine_has_no_unearned_verified_flag():
    spine = Registry().load()
    rows = yaml.safe_load((ROOT / "data/resolutions.yml").read_text())["resolutions"]
    items = [(c.id, c.source, c.verified) for c in spine.claims]
    items += [(w["id"], work_source(w), bool(w.get("verified"))) for w in spine.works]
    assert verification_problems(items, index_resolutions(rows)) == []


def test_brief_is_deterministic_and_dated_by_data():
    run = lambda: subprocess.run(  # noqa: E731
        [sys.executable, "scripts/ca.py", "brief", "robotics", "--json"],
        cwd=ROOT, capture_output=True, text=True, check=True,
    ).stdout
    first = run()
    assert first == run()
    data = yaml.safe_load(first)
    assert data["as_of"] != "undated"
    assert {"loops", "claims", "load_bearing", "questions"} <= data.keys()
    assert all(a["status"] != "discharged" for a in data["load_bearing"])


def test_brief_rejects_a_thirteenth_domain():
    r = subprocess.run([sys.executable, "scripts/ca.py", "brief", "astrology"], cwd=ROOT, capture_output=True, text=True)
    assert r.returncode == 1 and "closed set" in r.stderr
