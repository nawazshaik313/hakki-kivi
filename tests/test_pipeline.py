"""Tests run without BirdNET, Ollama or the internet (Gemma is replaced by a fake client)."""
import dataclasses
import json
from pathlib import Path

import pytest

from hakki_kivi import fieldcard, trip
from hakki_kivi.checklist import Checklist
from hakki_kivi.config import DATA_DIR, Settings
from hakki_kivi.detect import Detection, best_per_species, birdnet_week, load_detections_json, parse_birdnet_csv
from hakki_kivi.evaluate import summarise
from hakki_kivi.languages import normalise

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def settings(tmp_path):
    return dataclasses.replace(Settings(), output_dir=tmp_path, ollama_url="http://127.0.0.1:9")


def test_languages_always_start_with_english():
    assert normalise(["kn", "hi", "kn", "xx"]) == ["en", "kn", "hi"]
    assert normalise(["Telugu"]) == ["en", "te"]


def test_birdnet_week():
    import datetime as dt
    assert birdnet_week(dt.date(2026, 1, 1)) == 1
    assert birdnet_week(dt.date(2026, 11, 28)) == 44
    assert birdnet_week(dt.date(2026, 12, 31)) == 48


def test_parse_birdnet_csv(tmp_path):
    f = tmp_path / "clip.BirdNET.results.csv"
    f.write_text("Start (s),End (s),Scientific name,Common name,Confidence,File\n"
                 "0.0,3.0,Eudynamys scolopaceus,Asian Koel,0.9512,C:/walk/clip.wav\n", encoding="utf-8")
    [d] = parse_birdnet_csv(f, clip_name="clip.wav")
    assert d.common_name == "Asian Koel" and d.confidence == pytest.approx(0.9512)


def test_parse_raven_table(tmp_path):
    f = tmp_path / "clip.BirdNET.selection.table.txt"
    f.write_text("Selection\tBegin Time (s)\tEnd Time (s)\tCommon Name\tScientific Name\tConfidence\n"
                 "1\t3\t6\tIndian Robin\tCopsychus fulicatus\t0.77\n", encoding="utf-8")
    [d] = parse_birdnet_csv(f)
    assert d.scientific_name == "Copsychus fulicatus" and d.start_s == 3


def test_best_per_species_keeps_highest():
    ds = [Detection("a.wav", 0, 3, "X y", "X", 0.4), Detection("a.wav", 3, 6, "X y", "X", 0.8)]
    assert [d.confidence for d in best_per_species(ds)] == [0.8]


def test_checklist_loads_and_finds():
    cl = Checklist.load(DATA_DIR / "ballari_checklist.csv")
    assert len(cl) >= 25
    assert "Vulnerable" in cl.find("Pycnonotus xantholaemus").status
    assert cl.find(common_name="asian koel") is not None


def test_offline_fallback_when_ollama_missing(settings):
    dets = load_detections_json(ROOT / "samples" / "demo_detections.json")
    result = trip.process_detections(dets, settings, ["en", "kn"])
    trip.write_outputs(result, settings, ["en", "kn"], "Test walk")
    assert result.model_used.startswith("checklist")
    assert len(result.cards) == 5 and len(result.unsure) == 1  # 0.31 blackbird is unsure
    assert all(c.generated_by == "checklist" for c in result.cards)
    assert result.html_path.exists() and "Hakki Kivi" in result.html_path.read_text(encoding="utf-8")


class FakeClient:
    model = "fake-gemma"

    def __init__(self, reply):
        self.reply = reply
        self.prompts = []

    def chat_json(self, prompt, images=None):
        self.prompts.append(prompt)
        return self.reply


def test_card_is_grounded_and_multilingual():
    cl = Checklist.load(DATA_DIR / "ballari_checklist.csv")
    det = Detection("a.wav", 0, 3, "Pycnonotus xantholaemus", "Yellow-throated Bulbul", 0.8)
    reply = {"cards": {
        "en": {"name": "Yellow-throated Bulbul", "tip": "Yellow throat, among boulders", "challenge": "Look on rocks"},
        "kn": {"name": "ಹಳದಿ ಗಂಟಲಿನ ಪಿಕಳಾರ", "tip": "ಹಳದಿ ಗಂಟಲು", "challenge": "ಬಂಡೆಗಳ ಮೇಲೆ ನೋಡಿ"},
        "hi": {"name": "पीले गले वाली बुलबुल", "tip": "पीला गला", "challenge": "चट्टानों पर देखें"},
        "status": "Extinct",  # the model trying to invent a status must be ignored
    }}
    client = FakeClient(reply)
    card = fieldcard.make_card(det, cl.find(det.scientific_name), ["en", "kn", "hi"], client)
    assert card.generated_by == "fake-gemma"
    assert set(card.texts) == {"en", "kn", "hi"}
    assert "Vulnerable" in card.status  # status from checklist, not model
    assert "boulders" in client.prompts[0]  # checklist facts are passed in


def test_bad_model_reply_falls_back():
    det = Detection("a.wav", 0, 3, "Eudynamys scolopaceus", "Asian Koel", 0.9)
    card = fieldcard.make_card(det, None, ["en", "kn"], FakeClient({"nonsense": 1}))
    assert card.generated_by == "checklist" and card.texts["en"]["name"] == "Asian Koel"
    assert card.status == "Not on local checklist"


def test_parse_json_reply_tolerates_fences():
    assert fieldcard.parse_json_reply('```json\n{"a": 1}\n```') == {"a": 1}
    with pytest.raises(ValueError):
        fieldcard.parse_json_reply("no json here")


def test_evaluate(tmp_path):
    f = tmp_path / "log.csv"
    f.write_text("clip,scientific_name,common_name,confidence,status,on_local_list,result,your_check (right/wrong/unsure)\n"
                 "a,X,Koel,0.9,LC,True,card,right\n"
                 "b,Y,Robin,0.8,LC,True,card,wrong\n"
                 "c,Z,Blackbird,0.6,,False,card,right\n"
                 "d,W,Odd,0.2,,,unsure,\n", encoding="utf-8")
    out = summarise(f)
    assert "67% (2/3)" in out and "Blackbird" in out
