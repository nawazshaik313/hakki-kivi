"""Multilingual field cards written by Gemma running locally in Ollama.

Grounding rules (so the model cannot make things up):
- Species identity comes from BirdNET, never from Gemma.
- Conservation status, habitat and the ID tip come from the local checklist row.
- Gemma only rephrases those facts in each requested language and adds a
  "listen for it next time" challenge. If Gemma is unreachable, we fall back to a
  plain English card built only from the checklist.
"""
from __future__ import annotations

import base64
import json
import time
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass, field
from pathlib import Path

from .checklist import ChecklistEntry
from .detect import Detection
from .languages import name_of

SYSTEM_PROMPT = (
    "You write short field cards for birdwatchers walking outdoors in India. "
    "Use ONLY the facts given to you. Never add a new fact, number, location or status. "
    "If a fact is missing, leave that part out. Keep every line short enough to read in two seconds, "
    "because the reader should look back at the bird, not the screen. Reply with JSON only."
)


@dataclass
class FieldCard:
    clip: str
    scientific_name: str
    common_name: str
    confidence: float
    status: str
    on_local_list: bool
    texts: dict[str, dict] = field(default_factory=dict)  # lang code -> {"name","tip","challenge"}
    generated_by: str = "checklist"  # model tag, or "checklist" for the offline fallback
    seconds: float = 0.0

    def to_dict(self) -> dict:
        return asdict(self)


class OllamaClient:
    def __init__(self, base_url: str, model: str, timeout: int = 180):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout

    def _post(self, path: str, payload: dict) -> dict:
        req = urllib.request.Request(
            self.base_url + path,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))

    def available(self) -> bool:
        try:
            with urllib.request.urlopen(self.base_url + "/api/tags", timeout=5) as resp:
                tags = json.loads(resp.read().decode("utf-8"))
            names = {m.get("name", "") for m in tags.get("models", [])}
            return self.model in names or any(n.split(":")[0] == self.model.split(":")[0] for n in names)
        except (urllib.error.URLError, OSError, ValueError):
            return False

    def chat_json(self, prompt: str, images: list[bytes] | None = None) -> dict:
        message: dict = {"role": "user", "content": prompt}
        if images:
            message["images"] = [base64.b64encode(img).decode("ascii") for img in images]
        payload = {
            "model": self.model,
            "messages": [{"role": "system", "content": SYSTEM_PROMPT}, message],
            "format": "json",
            "stream": False,
            "options": {"temperature": 0.2},
        }
        reply = self._post("/api/chat", payload)
        content = reply.get("message", {}).get("content", "")
        return parse_json_reply(content)


def parse_json_reply(content: str) -> dict:
    """Parse the model's JSON, tolerating code fences or text around it."""
    content = content.strip()
    if content.startswith("```"):
        content = content.strip("`")
        content = content[content.find("{"):]
    start, end = content.find("{"), content.rfind("}")
    if start == -1 or end == -1:
        raise ValueError("Model reply contained no JSON object")
    return json.loads(content[start : end + 1])


def build_prompt(det: Detection, entry: ChecklistEntry | None, languages: list[str]) -> str:
    facts = {
        "english_name": det.common_name or (entry.common_name if entry else ""),
        "scientific_name": det.scientific_name,
        "identification_tip": entry.id_tip if entry else "",
        "habitat": entry.habitat if entry else "",
    }
    lang_list = ", ".join(f'"{c}" ({name_of(c)})' for c in languages)
    return (
        "Facts about a bird just heard on a walk:\n"
        f"{json.dumps(facts, ensure_ascii=False, indent=2)}\n\n"
        f"Write the card in these languages: {lang_list}.\n"
        "Return JSON shaped exactly like:\n"
        '{"cards": {"<language code>": {"name": "bird name in that language (transliterate the '
        'English name if you do not know a common local name)", "tip": "one line built only from '
        'identification_tip and habitat", "challenge": "one line: what to listen or look for next time, '
        'from the facts only"}}}\n'
        "Use the native script of each language."
    )


def checklist_card(det: Detection, entry: ChecklistEntry | None) -> dict[str, dict]:
    tip_parts = [p for p in [entry.id_tip if entry else "", entry.habitat if entry else ""] if p]
    return {
        "en": {
            "name": det.common_name or (entry.common_name if entry else det.scientific_name),
            "tip": ". ".join(tip_parts) or "Not on the local checklist yet: note where you heard it.",
            "challenge": "Next walk: try to see it and confirm the ID.",
        }
    }


def make_card(
    det: Detection,
    entry: ChecklistEntry | None,
    languages: list[str],
    client: OllamaClient | None,
) -> FieldCard:
    card = FieldCard(
        clip=det.clip,
        scientific_name=det.scientific_name,
        common_name=det.common_name or (entry.common_name if entry else ""),
        confidence=round(det.confidence, 3),
        # Status always comes from the checklist, never from the model.
        status=entry.status if entry else "Not on local checklist",
        on_local_list=entry is not None,
        texts=checklist_card(det, entry),
    )
    if client is None:
        return card
    started = time.perf_counter()
    try:
        reply = client.chat_json(build_prompt(det, entry, languages))
        cards = reply.get("cards", reply)
        texts: dict[str, dict] = {}
        for code in languages:
            block = cards.get(code) or cards.get(name_of(code)) or {}
            if isinstance(block, dict) and block.get("name"):
                texts[code] = {
                    "name": str(block.get("name", "")).strip(),
                    "tip": str(block.get("tip", "")).strip(),
                    "challenge": str(block.get("challenge", "")).strip(),
                }
        if "en" in texts:
            card.texts = texts
            card.generated_by = client.model
        else:
            card.texts.update(texts)
    except (urllib.error.URLError, OSError, ValueError, KeyError, TypeError):
        pass  # keep the grounded English fallback card
    card.seconds = round(time.perf_counter() - started, 2)
    return card


def identify_photo(image_path: str | Path, client: OllamaClient, candidates: list[str]) -> dict:
    """Fallback when there is no recording: ask Gemma's vision to pick from the local checklist.

    Gemma may only answer with a name from `candidates` (or "unknown"), which limits wrong guesses.
    """
    prompt = (
        "Which bird is in this photo? Answer ONLY with one name from this list, or \"unknown\":\n"
        + "\n".join(candidates)
        + '\nReturn JSON: {"common_name": "...", "confidence": "high|medium|low"}'
    )
    reply = client.chat_json(prompt, images=[Path(image_path).read_bytes()])
    name = str(reply.get("common_name", "unknown")).strip()
    if name not in candidates:
        name = "unknown"
    return {"common_name": name, "confidence": reply.get("confidence", "low")}
