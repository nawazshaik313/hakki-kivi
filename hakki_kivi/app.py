"""Gradio app. Run:  python -m hakki_kivi.app   then open http://localhost:7860

To use it from your phone with no internet: turn on the phone's hotspot (mobile data OFF),
connect the laptop to it, run with HAKKI_SHARE_LAN=1, and open http://<laptop-ip>:7860 on the phone.
"""
from __future__ import annotations

import dataclasses
import datetime as dt
import os

import gradio as gr

from .config import Settings
from .detect import load_detections_json
from .fieldcard import OllamaClient
from .languages import DEFAULT_LANGUAGES, LANGUAGES
from .trip import analyse_walk, process_detections, write_outputs

LABELS = list(LANGUAGES.values())
CODE_BY_LABEL = {v: k for k, v in LANGUAGES.items()}


def _settings(lat: float, lon: float, min_conf: float, model: str) -> Settings:
    base = Settings()
    return dataclasses.replace(base, latitude=float(lat), longitude=float(lon),
                               min_confidence=float(min_conf), model=model.strip() or base.model)


def run(files, demo_json, walk_name, lat, lon, min_conf, langs, model, use_gemma):
    settings = _settings(lat, lon, min_conf, model)
    codes = [CODE_BY_LABEL[label] for label in (langs or [])]
    if demo_json is not None:
        detections = load_detections_json(demo_json if isinstance(demo_json, str) else demo_json.name)
        result = process_detections(detections, settings, ["en", *codes], use_gemma)
        write_outputs(result, settings, ["en", *codes], walk_name or "Walk", dt.date.today())
    else:
        paths = [f if isinstance(f, str) else f.name for f in (files or [])]
        if not paths:
            return "<p>Add some bird-call recordings first.</p>", None, None
        result = analyse_walk(paths, settings, codes, walk_name=walk_name or "Walk", use_gemma=use_gemma)
    page = result.html_path.read_text(encoding="utf-8")
    return page, str(result.html_path), str(result.csv_path)


def status_line(model: str) -> str:
    settings = Settings()
    client = OllamaClient(settings.ollama_url, model.strip() or settings.model)
    if client.available():
        return f"✅ {client.model} is running locally in Ollama. No internet needed."
    return (f"⚠️ {client.model} not found in Ollama. Run `ollama pull {client.model}`. "
            "Cards will use the checklist only until then.")


def build() -> gr.Blocks:
    s = Settings()
    with gr.Blocks(title="Hakki Kivi · offline bird walk cards") as demo:
        gr.Markdown(
            "# 🐦 Hakki Kivi (ಹಕ್ಕಿ ಕಿವಿ, *Bird Ear*)\n"
            "Record bird calls on your walk with the phone in your pocket. Afterwards, drop the clips here. "
            "BirdNET names the birds and a local Gemma writes a short multilingual field card. "
            "**Everything runs on this machine. No internet, no account, no cost.**"
        )
        with gr.Row():
            with gr.Column():
                files = gr.File(label="Bird-call recordings (wav, mp3, m4a…)", file_count="multiple")
                with gr.Accordion("No recordings yet? Try the demo detections", open=False):
                    demo_json = gr.File(label="detections JSON (see samples/demo_detections.json)")
                walk_name = gr.Textbox(label="Walk name", value="Morning walk, Ballari")
                with gr.Row():
                    lat = gr.Number(label="Latitude", value=s.latitude)
                    lon = gr.Number(label="Longitude", value=s.longitude)
                langs = gr.CheckboxGroup(
                    LABELS[1:], value=[LANGUAGES[c] for c in DEFAULT_LANGUAGES if c != "en"],
                    label="Card languages (English is always included)",
                )
                min_conf = gr.Slider(0.1, 0.95, value=s.min_confidence, step=0.05,
                                     label="Minimum BirdNET confidence (below this = 'unsure')")
                with gr.Row():
                    model = gr.Textbox(label="Ollama model", value=s.model)
                    use_gemma = gr.Checkbox(label="Write cards with Gemma", value=True)
                check = gr.Button("Check model")
                status = gr.Markdown()
                go = gr.Button("Make my trip card", variant="primary")
            with gr.Column():
                card = gr.HTML()
                html_file = gr.File(label="Trip card (open, then print or save as PDF)")
                csv_file = gr.File(label="Walk log CSV (fill the 'your_check' column for your eval)")
        check.click(status_line, inputs=model, outputs=status)
        go.click(run, inputs=[files, demo_json, walk_name, lat, lon, min_conf, langs, model, use_gemma],
                 outputs=[card, html_file, csv_file])
    return demo


def main() -> None:
    host = "0.0.0.0" if os.getenv("HAKKI_SHARE_LAN") == "1" else "127.0.0.1"
    build().launch(server_name=host, server_port=int(os.getenv("HAKKI_PORT", "7860")))


if __name__ == "__main__":
    main()
