"""Local bird checklist used to ground the AI's field cards.

Gemma never decides a bird's conservation status: that comes from this table, so the model
cannot invent it. Extend data/ballari_checklist.csv with the full Daroji list (see README).
"""
from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ChecklistEntry:
    common_name: str
    scientific_name: str
    status: str          # e.g. "Least Concern", "Near Threatened", "Vulnerable"
    habitat: str
    id_tip: str
    source: str


class Checklist:
    def __init__(self, entries: list[ChecklistEntry]):
        self.entries = entries
        self._by_sci = {e.scientific_name.lower(): e for e in entries}
        self._by_common = {e.common_name.lower(): e for e in entries}

    @classmethod
    def load(cls, path: str | Path) -> "Checklist":
        path = Path(path)
        if not path.exists():
            return cls([])
        with path.open(encoding="utf-8", newline="") as fh:
            rows = csv.DictReader(fh)
            entries = [
                ChecklistEntry(
                    common_name=(r.get("common_name") or "").strip(),
                    scientific_name=(r.get("scientific_name") or "").strip(),
                    status=(r.get("status") or "").strip(),
                    habitat=(r.get("habitat") or "").strip(),
                    id_tip=(r.get("id_tip") or "").strip(),
                    source=(r.get("source") or "").strip(),
                )
                for r in rows
                if (r.get("scientific_name") or "").strip()
            ]
        return cls(entries)

    def find(self, scientific_name: str = "", common_name: str = "") -> ChecklistEntry | None:
        if scientific_name and scientific_name.lower() in self._by_sci:
            return self._by_sci[scientific_name.lower()]
        if common_name and common_name.lower() in self._by_common:
            return self._by_common[common_name.lower()]
        return None

    def __len__(self) -> int:
        return len(self.entries)
