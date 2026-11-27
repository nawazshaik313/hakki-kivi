"""Walk pipeline: audio clips -> BirdNET -> checklist grounding -> Gemma cards -> trip card.

The trip card is a single printable HTML page. Print it (or save as PDF) and take it on your
next walk, so the screen stays in your pocket.
"""
from __future__ import annotations

import csv
import datetime as dt
import html
import json
from dataclasses import dataclass, field
from pathlib import Path

from .checklist import Checklist
from .config import Settings
from .detect import AUDIO_EXTENSIONS, Detection, best_per_species, birdnet_week, run_birdnet
from .fieldcard import FieldCard, OllamaClient, make_card
from .languages import name_of, normalise


@dataclass
class TripResult:
    cards: list[FieldCard] = field(default_factory=list)
    unsure: list[Detection] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    model_used: str = "checklist only (Gemma not reachable)"
    html_path: Path | None = None
    csv_path: Path | None = None
    json_path: Path | None = None


def collect_clips(paths: list[str | Path]) -> list[Path]:
    clips: list[Path] = []
    for p in map(Path, paths):
        if p.is_dir():
            clips.extend(sorted(c for c in p.iterdir() if c.suffix.lower() in AUDIO_EXTENSIONS))
        elif p.suffix.lower() in AUDIO_EXTENSIONS:
            clips.append(p)
    return clips


def process_detections(
    detections: list[Detection],
    settings: Settings,
    languages: list[str],
    use_gemma: bool = True,
) -> TripResult:
    checklist = Checklist.load(settings.checklist_path)
    client = OllamaClient(settings.ollama_url, settings.model, settings.request_timeout)
    if not (use_gemma and client.available()):
        client = None
    result = TripResult(model_used=settings.model if client else TripResult.model_used)
    for det in best_per_species(detections):
        if det.confidence < settings.min_confidence:
            result.unsure.append(det)
            continue
        entry = checklist.find(det.scientific_name, det.common_name)
        result.cards.append(make_card(det, entry, languages, client))
    return result


def analyse_walk(
    clip_paths: list[str | Path],
    settings: Settings | None = None,
    languages: list[str] | None = None,
    walk_date: dt.date | None = None,
    walk_name: str = "Walk",
    use_gemma: bool = True,
) -> TripResult:
    settings = settings or Settings()
    languages = normalise(languages)
    detections: list[Detection] = []
    errors: list[str] = []
    for clip in collect_clips(clip_paths):
        try:
            detections.extend(
                run_birdnet(clip, settings.latitude, settings.longitude, birdnet_week(walk_date), min_conf=0.1)
            )
        except Exception as exc:  # one bad clip should not stop the walk
            errors.append(f"{clip.name}: {exc}")
    result = process_detections(detections, settings, languages, use_gemma)
    result.errors = errors
    write_outputs(result, settings, languages, walk_name, walk_date)
    return result


def write_outputs(
    result: TripResult,
    settings: Settings,
    languages: list[str],
    walk_name: str = "Walk",
    walk_date: dt.date | None = None,
) -> TripResult:
    walk_date = walk_date or dt.date.today()
    stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    out = Path(settings.output_dir)
    out.mkdir(parents=True, exist_ok=True)
    base = out / f"trip-{stamp}"

    result.csv_path = base.with_suffix(".csv")
    with result.csv_path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(["clip", "scientific_name", "common_name", "confidence", "status",
                         "on_local_list", "result", "your_check (right/wrong/unsure)"])
        for c in result.cards:
            writer.writerow([c.clip, c.scientific_name, c.common_name, c.confidence, c.status,
                             c.on_local_list, "card", ""])
        for d in result.unsure:
            writer.writerow([d.clip, d.scientific_name, d.common_name, round(d.confidence, 3), "",
                             "", "unsure", ""])

    result.json_path = base.with_suffix(".json")
    result.json_path.write_text(
        json.dumps(
            {
                "walk": walk_name,
                "date": walk_date.isoformat(),
                "location": [settings.latitude, settings.longitude],
                "model": result.model_used,
                "languages": languages,
                "cards": [c.to_dict() for c in result.cards],
                "unsure": [d.to_dict() for d in result.unsure],
                "errors": result.errors,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    result.html_path = base.with_suffix(".html")
    result.html_path.write_text(
        render_trip_card(result, languages, walk_name, walk_date, settings), encoding="utf-8"
    )
    return result


def _status_class(status: str) -> str:
    s = status.lower()
    if "vulnerable" in s or "endangered" in s:
        return "vu"
    if "near threatened" in s:
        return "nt"
    return "lc"


def render_trip_card(
    result: TripResult,
    languages: list[str],
    walk_name: str,
    walk_date: dt.date,
    settings: Settings,
) -> str:
    e = html.escape
    cards_html = []
    for c in result.cards:
        rows = []
        for code in languages:
            t = c.texts.get(code)
            if not t:
                continue
            rows.append(
                f'<div class="lang"><span class="code">{e(name_of(code))}</span>'
                f'<b>{e(t.get("name", ""))}</b><br>{e(t.get("tip", ""))}'
                f'<br><i>{e(t.get("challenge", ""))}</i></div>'
            )
        cards_html.append(
            f'<section class="card">'
            f'<h2>{e(c.common_name)} <small><i>{e(c.scientific_name)}</i></small></h2>'
            f'<p class="meta"><span class="status {_status_class(c.status)}">{e(c.status)}</span> '
            f'· BirdNET {c.confidence:.0%} · clip {e(c.clip)}'
            f'{"" if c.on_local_list else " · <b>not on local checklist: double-check</b>"}</p>'
            f'{"".join(rows)}</section>'
        )
    unsure_html = "".join(
        f"<li>{e(d.common_name or d.scientific_name)} ({d.confidence:.0%}, {e(d.clip)})</li>"
        for d in result.unsure
    )
    errors_html = "".join(f"<li>{e(x)}</li>" for x in result.errors)
    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Hakki Kivi trip card · {e(walk_name)}</title>
<style>
 body {{ font-family: "Noto Sans", "Noto Sans Kannada", "Noto Sans Devanagari", system-ui, sans-serif;
        max-width: 780px; margin: 24px auto; padding: 0 16px; color: #1f2a1f; }}
 header {{ border-bottom: 3px solid #3d6b35; margin-bottom: 16px; }}
 h1 {{ margin: 0 0 4px; color: #2f5a28; }}
 .card {{ border: 1px solid #c9d8c5; border-radius: 10px; padding: 12px 16px; margin: 12px 0; break-inside: avoid; }}
 .card h2 {{ margin: 0; font-size: 1.15rem; }} .card small {{ color: #555; font-weight: normal; }}
 .meta {{ font-size: .85rem; color: #444; margin: 4px 0 8px; }}
 .status {{ padding: 1px 8px; border-radius: 99px; font-weight: 600; }}
 .lc {{ background: #e3f1df; }} .nt {{ background: #fff1c7; }} .vu {{ background: #ffd9d2; }}
 .lang {{ margin: 6px 0; line-height: 1.45; }}
 .code {{ display: inline-block; min-width: 82px; font-size: .75rem; color: #3d6b35; text-transform: uppercase; }}
 footer {{ font-size: .75rem; color: #666; margin-top: 24px; }}
 @media print {{ body {{ margin: 0; }} }}
</style></head><body>
<header><h1>🐦 {e(walk_name)}</h1>
<p>{walk_date.isoformat()} · {settings.latitude:.3f}, {settings.longitude:.3f} ·
 {len(result.cards)} species · written offline by <b>{e(result.model_used)}</b></p></header>
{"".join(cards_html) or "<p>No confident detections. Try longer clips closer to the bird.</p>"}
{f"<h3>Unsure (below {settings.min_confidence:.0%}, no card written)</h3><ul>{unsure_html}</ul>" if unsure_html else ""}
{f"<h3>Clips that failed</h3><ul>{errors_html}</ul>" if errors_html else ""}
<footer>Hakki Kivi · bird ID by BirdNET (open source) · cards by an open-weight model running locally.
Conservation status comes from the local checklist, not from the AI. Fold this page, pocket the phone, go listen.</footer>
</body></html>"""
