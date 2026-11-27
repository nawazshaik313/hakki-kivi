"""Honest scoring for your walk. After the walk, open the log CSV and write right / wrong / unsure
in the last column for every row (check against your own sighting, a photo, or a birder friend).
Then run:  python -m hakki_kivi --eval trips/trip-....csv
"""
from __future__ import annotations

import csv
from collections import Counter
from pathlib import Path


def summarise(path: str | Path) -> str:
    with Path(path).open(encoding="utf-8", newline="") as fh:
        rows = list(csv.DictReader(fh))
    check_col = next((k for k in (rows[0].keys() if rows else []) if k.startswith("your_check")), None)
    carded = [r for r in rows if r.get("result") == "card"]
    marks = Counter((r.get(check_col) or "").strip().lower() for r in carded) if check_col else Counter()
    judged = marks["right"] + marks["wrong"]
    lines = [
        f"Detections with a card: {len(carded)}",
        f"Marked unsure by the app: {sum(1 for r in rows if r.get('result') == 'unsure')}",
        f"Your check: right={marks['right']} wrong={marks['wrong']} unsure={marks['unsure']} "
        f"unchecked={len(carded) - judged - marks['unsure']}",
    ]
    if judged:
        lines.append(f"Hit rate on cards you could judge: {marks['right'] / judged:.0%} ({marks['right']}/{judged})")
    off_list = [r["common_name"] for r in carded if str(r.get("on_local_list")).lower() == "false"]
    if off_list:
        lines.append("Not on local checklist (check these first): " + ", ".join(off_list))
    return "\n".join(lines)
