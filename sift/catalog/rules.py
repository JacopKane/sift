"""Loading and applying the path catalog.

Pure string and stat work — no model, no network, no cost. Everything this layer
settles is something the model never has to be asked about.
"""

from __future__ import annotations

from collections.abc import Sequence
from fnmatch import fnmatch
from pathlib import Path

import yaml
from pydantic import BaseModel

from sift.models import Verdict

CATALOG_PATH = Path(__file__).parent / "catalog.yaml"


class CatalogRule(BaseModel):
    id: str
    label: str
    match: str
    verdict: Verdict
    restore: str | None = None
    restore_time: str | None = None
    requires_sibling: str | None = None


class Catalog:
    def __init__(self, rules: Sequence[CatalogRule], home: Path) -> None:
        self._rules = tuple(rules)
        self._home = home

    def recognise(self, path: Path, *, is_dir: bool) -> CatalogRule | None:
        """The first rule that claims *path*, or None if the catalog can't name it."""
        if not is_dir:
            # Directories are classified, not files. Asking about 47,000 files is
            # impossible; asking about the 50 directories holding them is not.
            return None
        return next((rule for rule in self._rules if self._matches(rule, path)), None)

    def _matches(self, rule: CatalogRule, path: Path) -> bool:
        if not self._path_matches(rule.match, path):
            return False
        if rule.requires_sibling is None:
            return True
        # Generic names only count when their marker is beside them: `target` is
        # build output next to a Cargo.toml, and somebody's folder without one.
        return (path.parent / rule.requires_sibling).exists()

    def _path_matches(self, pattern: str, path: Path) -> bool:
        if pattern.startswith("**/"):
            return fnmatch(path.name, pattern[3:])
        if pattern.startswith("~/"):
            pattern = str(self._home / pattern[2:])
        return fnmatch(str(path), pattern)


def load_catalog(home: Path | None = None) -> Catalog:
    """Read catalog.yaml, resolving ~/... rules against *home*.

    *home* is a parameter rather than always ``Path.home()`` so the catalog can be
    pointed at a fixture — which means tests exercise the real rules rather than
    a parallel set written for testing.
    """
    document = yaml.safe_load(CATALOG_PATH.read_text(encoding="utf-8"))
    rules = [CatalogRule.model_validate(entry) for entry in document["rules"]]
    return Catalog(rules, home or Path.home())
