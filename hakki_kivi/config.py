"""Settings for Hakki Kivi. Every value can be overridden with an environment variable."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

PACKAGE_DIR = Path(__file__).resolve().parent
PROJECT_DIR = PACKAGE_DIR.parent
DATA_DIR = PROJECT_DIR / "data"


@dataclass
class Settings:
    # Local Ollama server (open-weight model, runs on your own machine).
    ollama_url: str = field(default_factory=lambda: os.getenv("HAKKI_OLLAMA_URL", "http://localhost:11434"))
    # Gemma 4 E2B quantised. Use gemma4:e4b-it-qat on 16 GB RAM, or any other Ollama model tag.
    model: str = field(default_factory=lambda: os.getenv("HAKKI_MODEL", "gemma4:e2b-it-qat"))
    # Default walk location: Ballari, Karnataka (Daroji/Hampi is ~15.25 N, 76.55 E).
    latitude: float = field(default_factory=lambda: float(os.getenv("HAKKI_LAT", "15.14")))
    longitude: float = field(default_factory=lambda: float(os.getenv("HAKKI_LON", "76.92")))
    # Detections below this BirdNET confidence are shown as "unsure" and get no AI card.
    min_confidence: float = field(default_factory=lambda: float(os.getenv("HAKKI_MIN_CONF", "0.5")))
    checklist_path: Path = field(default_factory=lambda: Path(os.getenv("HAKKI_CHECKLIST", DATA_DIR / "ballari_checklist.csv")))
    output_dir: Path = field(default_factory=lambda: Path(os.getenv("HAKKI_OUT", PROJECT_DIR / "trips")))
    request_timeout: int = field(default_factory=lambda: int(os.getenv("HAKKI_TIMEOUT", "180")))
