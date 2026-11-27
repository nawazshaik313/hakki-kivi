"""Languages the field card can be written in.

Gemma 4 is trained on 140+ languages, so any of these can be requested. English is always
included so a reader can check the card. Quality differs by language: test yours before a walk.
"""
from __future__ import annotations

LANGUAGES: dict[str, str] = {
    "en": "English",
    "kn": "Kannada (ಕನ್ನಡ)",
    "hi": "Hindi (हिन्दी)",
    "te": "Telugu (తెలుగు)",
    "ta": "Tamil (தமிழ்)",
    "ml": "Malayalam (മലയാളം)",
    "mr": "Marathi (मराठी)",
    "bn": "Bengali (বাংলা)",
    "gu": "Gujarati (ગુજરાતી)",
    "ur": "Urdu (اردو)",
    "pa": "Punjabi (ਪੰਜਾਬੀ)",
    "or": "Odia (ଓଡ଼ିଆ)",
    "es": "Spanish",
    "fr": "French",
    "de": "German",
}

DEFAULT_LANGUAGES = ["en", "kn", "hi"]


def normalise(codes: list[str] | None) -> list[str]:
    """Return a de-duplicated list of known codes, always starting with English."""
    result = ["en"]
    for code in codes or []:
        code = code.strip().lower()
        # Accept either a code ("kn") or a label ("Kannada (ಕನ್ನಡ)").
        if code not in LANGUAGES:
            matches = [k for k, v in LANGUAGES.items() if v.lower().startswith(code)]
            if not matches:
                continue
            code = matches[0]
        if code not in result:
            result.append(code)
    return result


def name_of(code: str) -> str:
    return LANGUAGES.get(code, code).split(" (")[0]
