"""Bird-sound detection with BirdNET-Analyzer (open source, runs offline).

We call the BirdNET command-line tool and read its CSV output, so the code keeps working
across BirdNET versions. Install it with:  pip install birdnet_analyzer
"""
from __future__ import annotations

import csv
import datetime as dt
import json
import shutil
import subprocess
import sys
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path

AUDIO_EXTENSIONS = {".wav", ".mp3", ".flac", ".ogg", ".m4a", ".aac", ".opus"}


@dataclass
class Detection:
    clip: str
    start_s: float
    end_s: float
    scientific_name: str
    common_name: str
    confidence: float

    def to_dict(self) -> dict:
        return asdict(self)


class BirdNetNotInstalled(RuntimeError):
    pass


def birdnet_week(date: dt.date | None = None) -> int:
    """BirdNET splits the year into 48 'weeks' (4 per month)."""
    date = date or dt.date.today()
    return min(48, (date.month - 1) * 4 + min(4, (date.day - 1) // 7 + 1))


def _header_key(row: dict, *candidates: str) -> str | None:
    lowered = {k.lower().strip(): k for k in row}
    for c in candidates:
        if c in lowered:
            return lowered[c]
    return None


def parse_birdnet_csv(path: str | Path, clip_name: str | None = None) -> list[Detection]:
    """Parse BirdNET's CSV ('csv') or Raven table ('table') result files."""
    path = Path(path)
    delimiter = "\t" if path.suffix.lower() == ".txt" else ","
    detections: list[Detection] = []
    with path.open(encoding="utf-8", newline="") as fh:
        for row in csv.DictReader(fh, delimiter=delimiter):
            k_sci = _header_key(row, "scientific name", "scientific_name")
            k_com = _header_key(row, "common name", "common_name")
            k_conf = _header_key(row, "confidence")
            k_start = _header_key(row, "start (s)", "begin time (s)", "start")
            k_end = _header_key(row, "end (s)", "end time (s)", "end")
            k_file = _header_key(row, "file", "begin path")
            if not (k_sci and k_conf):
                continue
            clip = clip_name or (Path(row[k_file]).name if k_file and row.get(k_file) else path.stem)
            detections.append(
                Detection(
                    clip=clip,
                    start_s=float(row.get(k_start) or 0) if k_start else 0.0,
                    end_s=float(row.get(k_end) or 0) if k_end else 0.0,
                    scientific_name=row[k_sci].strip(),
                    common_name=(row.get(k_com) or "").strip() if k_com else "",
                    confidence=float(row[k_conf]),
                )
            )
    return detections


def _birdnet_command() -> list[str]:
    try:
        import birdnet_analyzer  # noqa: F401
    except ImportError as exc:
        if shutil.which("birdnet-analyze"):
            return ["birdnet-analyze"]
        raise BirdNetNotInstalled(
            "BirdNET-Analyzer is not installed. Run: pip install birdnet_analyzer"
        ) from exc
    return [sys.executable, "-m", "birdnet_analyzer.analyze"]


def run_birdnet(
    clip: str | Path,
    latitude: float,
    longitude: float,
    week: int | None = None,
    min_conf: float = 0.1,
) -> list[Detection]:
    """Run BirdNET on one audio file and return every detection above min_conf."""
    clip = Path(clip)
    week = week or birdnet_week()
    with tempfile.TemporaryDirectory() as out:
        cmd = _birdnet_command() + [
            str(clip),
            "-o", out,
            "--lat", str(latitude),
            "--lon", str(longitude),
            "--week", str(week),
            "--min_conf", str(min_conf),
            "--rtype", "csv",
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True)
        if proc.returncode != 0:
            raise RuntimeError(f"BirdNET failed on {clip.name}:\n{proc.stderr[-1500:]}")
        results: list[Detection] = []
        for result_file in Path(out).rglob("*.csv"):
            results.extend(parse_birdnet_csv(result_file, clip_name=clip.name))
        return results


def best_per_species(detections: list[Detection]) -> list[Detection]:
    """Keep the single most confident detection of each species in each clip."""
    best: dict[tuple[str, str], Detection] = {}
    for d in detections:
        key = (d.clip, d.scientific_name)
        if key not in best or d.confidence > best[key].confidence:
            best[key] = d
    return sorted(best.values(), key=lambda d: (d.clip, -d.confidence))


def load_detections_json(path: str | Path) -> list[Detection]:
    """Demo mode: read detections saved earlier (or written by hand) instead of running BirdNET."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return [Detection(**item) for item in data]
