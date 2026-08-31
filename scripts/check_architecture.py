"""Deterministic checks for HDM's pure domain boundary."""

from __future__ import annotations

import ast
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
DOMAIN_ROOT = REPOSITORY_ROOT / "backend" / "hdm" / "domain"
FORBIDDEN_IMPORT_ROOTS = {
    "asyncio",
    "ctypes",
    "http",
    "os",
    "pathlib",
    "shutil",
    "socket",
    "subprocess",
    "urllib",
}


def imported_roots(node: ast.AST) -> tuple[str, ...]:
    if isinstance(node, ast.Import):
        return tuple(alias.name.split(".", 1)[0] for alias in node.names)
    if isinstance(node, ast.ImportFrom) and node.module:
        return (node.module.split(".", 1)[0],)
    return ()


def main() -> int:
    failures: list[str] = []
    for path in sorted(DOMAIN_ROOT.glob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            for root in imported_roots(node):
                if root in FORBIDDEN_IMPORT_ROOTS:
                    failures.append(
                        f"{path.relative_to(REPOSITORY_ROOT)}:{node.lineno}: "
                        f"domain imports forbidden I/O module {root!r}"
                    )
    if failures:
        print("Architecture check failed:")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("Architecture check passed: domain layer is I/O-free.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
