"""Command line:  python -m hakki_kivi walk/ --lang kn hi te --name "Daroji, Saturday"

  python -m hakki_kivi CLIPS...            analyse recordings (files or folders)
  python -m hakki_kivi --demo FILE.json    use saved detections instead of BirdNET
  python -m hakki_kivi --eval LOG.csv      score a walk log you have checked by hand
"""
from __future__ import annotations

import argparse
import dataclasses
import datetime as dt
import sys

from .config import Settings
from .detect import load_detections_json
from .evaluate import summarise
from .languages import LANGUAGES, normalise
from .trip import analyse_walk, process_detections, write_outputs


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="hakki_kivi", description="Offline multilingual bird-walk field cards")
    p.add_argument("clips", nargs="*", help="audio files or folders")
    p.add_argument("--lang", nargs="*", default=["kn", "hi"],
                   help=f"language codes ({', '.join(LANGUAGES)}); English is always added")
    p.add_argument("--name", default="Walk", help="walk name for the trip card")
    p.add_argument("--date", help="walk date YYYY-MM-DD (sets BirdNET's season)")
    p.add_argument("--lat", type=float)
    p.add_argument("--lon", type=float)
    p.add_argument("--min-conf", type=float)
    p.add_argument("--model", help="Ollama model tag, e.g. gemma4:e4b-it-qat")
    p.add_argument("--no-gemma", action="store_true", help="checklist-only cards")
    p.add_argument("--demo", help="detections JSON instead of running BirdNET")
    p.add_argument("--eval", help="walk log CSV with the 'your_check' column filled in")
    a = p.parse_args(argv)

    if a.eval:
        print(summarise(a.eval))
        return 0

    s = Settings()
    s = dataclasses.replace(
        s,
        latitude=a.lat if a.lat is not None else s.latitude,
        longitude=a.lon if a.lon is not None else s.longitude,
        min_confidence=a.min_conf if a.min_conf is not None else s.min_confidence,
        model=a.model or s.model,
    )
    langs = normalise(a.lang)
    date = dt.date.fromisoformat(a.date) if a.date else None
    if a.demo:
        result = process_detections(load_detections_json(a.demo), s, langs, use_gemma=not a.no_gemma)
        write_outputs(result, s, langs, a.name, date)
    elif a.clips:
        result = analyse_walk(a.clips, s, langs, walk_date=date, walk_name=a.name, use_gemma=not a.no_gemma)
    else:
        p.print_help()
        return 1

    print(f"Model: {result.model_used}")
    for c in result.cards:
        print(f"  ✓ {c.common_name} ({c.confidence:.0%}) [{c.status}] {c.seconds}s")
    for d in result.unsure:
        print(f"  ? {d.common_name or d.scientific_name} ({d.confidence:.0%}) unsure")
    for err in result.errors:
        print(f"  ! {err}", file=sys.stderr)
    print(f"Trip card: {result.html_path}\nLog: {result.csv_path}")
    return 0
