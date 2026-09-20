#!/usr/bin/env python3
"""The layering law — core stays lean, and the build fails when it stops being lean.

**The rule:** ``core/`` may import the standard library, ``pyyaml``, and other ``core``
modules. Nothing else. Ever. An addon may import core plus what it declares.

Why enforce it mechanically rather than by review: a dependency creeps in through a
*function-local* import that no top-of-file grep will find, and six months later
``make check`` needs a GPU. This walks the AST, so a local import counts exactly like a
top-level one. On research-anything's first run the equivalent check found two hidden
edges nobody knew about.

Exit codes: ``0`` green, ``1`` a violation, ``2`` the gate could not run.
"""

from __future__ import annotations

import ast
import sys
import sysconfig
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
PKG = SRC / "control_anything"

#: The ONLY third-party packages the core may touch. Adding one here is a deliberate act:
#: it widens what `make check` needs on a bare machine, so it is reviewed as a decision.
CORE_THIRD_PARTY: frozenset[str] = frozenset({"yaml"})


def _stdlib_names() -> frozenset[str]:
    """Top-level stdlib module names for this interpreter."""
    names = set(sys.stdlib_module_names)
    # `sysconfig` is consulted so the gate behaves the same on a trimmed distro build.
    if sysconfig.get_path("stdlib"):
        names.add("sysconfig")
    return frozenset(names)


STDLIB = _stdlib_names()


def _imports(path: Path) -> list[tuple[str, int]]:
    """Every imported top-level module name in a file, with its line number.

    Walks the whole tree, so imports inside functions, methods, ``try`` blocks and
    ``if TYPE_CHECKING`` are all caught.
    """
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except SyntaxError as exc:
        raise SystemExit(f"✗ layers: cannot parse {path.relative_to(ROOT)}: {exc}")

    found: list[tuple[str, int]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                found.append((alias.name.split(".")[0], node.lineno))
        elif isinstance(node, ast.ImportFrom):
            if node.level:  # relative import -> same package, always fine
                continue
            if node.module:
                found.append((node.module.split(".")[0], node.lineno))
    return found


def _is_internal(module: str) -> bool:
    return module == "control_anything"


def main() -> int:
    if not PKG.is_dir():
        print(f"✗ layers: package not found at {PKG}", file=sys.stderr)
        return 2

    violations: list[str] = []
    core_files = sorted((PKG / "core").rglob("*.py"))

    for path in core_files:
        rel = path.relative_to(ROOT)
        for module, lineno in _imports(path):
            if module in STDLIB or _is_internal(module) or module in CORE_THIRD_PARTY:
                continue
            violations.append(
                f"{rel}:{lineno} core imports third-party {module!r} "
                f"(allowed: stdlib + {sorted(CORE_THIRD_PARTY)} + control_anything)"
            )

    # Core must never reach into addons, even via the package root.
    for path in core_files:
        text = path.read_text(encoding="utf-8")
        if "addons" in text and "control_anything.addons" in text:
            violations.append(
                f"{path.relative_to(ROOT)} references control_anything.addons — "
                "core must reach addons through a seam, never by import"
            )

    # pyproject must not have drifted from what the core actually needs.
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    if "pyyaml" not in pyproject.lower():
        violations.append("pyproject.toml no longer declares pyyaml, which the core imports")

    if violations:
        print(f"✗ layers: {len(violations)} violation(s)", file=sys.stderr)
        for violation in violations:
            print(f"    - {violation}", file=sys.stderr)
        return 1

    print(
        f"✓ layers: {len(core_files)} core file(s) import only stdlib + "
        f"{sorted(CORE_THIRD_PARTY)} + control_anything"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
