## What I Built

**Hakki Kivi** (ಹಕ್ಕಿ ಕಿವಿ, Kannada for "Bird Ear") is an offline, multilingual bird-walk companion built on one rule: **walk first, screen last.**

- **On the walk**, your phone stays in your pocket in airplane mode, recording bird calls with its normal voice recorder. No app to stare at.
- **After the walk**, you drop the clips into Hakki Kivi on your laptop, still offline:
  - **BirdNET** names each bird and shows how confident it is.
  - Each species is checked against a **local checklist** of birds around Ballari and Daroji, Karnataka. Daroji Sloth Bear Sanctuary near Hampi is a BirdLife Important Bird Area with 189 recorded species.
  - **Gemma, an open-weight model running locally in Ollama,** writes a short **field card** for each bird: its name, one tip for recognising it, and a "listen for it next time" challenge.
- Cards are written in **any mix of languages you choose**: English plus Kannada, Hindi, Telugu, Tamil, Malayalam, Marathi, Bengali, Gujarati, Urdu, Punjabi, Odia and more. A Kannada-speaking grandparent, a Hindi-speaking friend and an English-speaking bird club can all read the same walk.
- You get a **one-page printable trip card**. Fold it, pocket the phone, and go back out to *see* the birds you heard. Screen time is the last two minutes of the trip, and it sends you outside again.

**Who it's for:** students, families and bird clubs in places with patchy mobile signal, like the boulder country around Hampi and Daroji, who want to learn the birds around them in their own language.

## Demo

- Repository with setup steps and a demo you can run without recordings: https://github.com/nawazshaik313/hakki-kivi
- Try it in one command, no recordings needed:
  ```bash
  python -m hakki_kivi --demo samples/demo_detections.json --lang kn hi te --name "Demo walk"
  ```
- Sample output trip card: `docs/sample_trip_card_checklist_mode.html` in the repo.
- Video demo: [ADD YOUTUBE LINK]

## Code

{% github nawazshaik313/hakki-kivi %}

https://github.com/nawazshaik313/hakki-kivi

- `hakki_kivi/detect.py`: runs BirdNET-Analyzer offline and parses its results.
- `hakki_kivi/fieldcard.py`: grounded multilingual prompt to Gemma through Ollama's local API, with a safe fallback.
- `hakki_kivi/trip.py`: walk pipeline, printable trip card and CSV walk log.
- `hakki_kivi/app.py`: Gradio app that can be opened from a phone over a hotspot with no internet.
- `hakki_kivi/evaluate.py`: scores the walk honestly from your own right/wrong checks.
- `tests/`: 12 tests that run with no models and no internet, including an HTTP test against a fake Ollama server.

## How I Built It

**Open-source AI at the core:**

| Piece | Open component | Role |
|---|---|---|
| Bird sound ID | **BirdNET-Analyzer** (open source) | Identifies species from audio on the laptop, filtered by location and season |
| Language model | **Gemma 4 E2B** (`gemma4:e2b-it-qat`, open weights, Apache 2.0) | Writes the multilingual field cards |
| Local inference | **Ollama** | Serves Gemma on `localhost`; no cloud, no API key |
| UI | **Gradio** | Simple app, reachable from the phone over a local hotspot |

**Pipeline:** phone voice recorder (airplane mode) → BirdNET (top species and confidence per clip) → match against `data/ballari_checklist.csv` → Gemma 4 E2B in Ollama writes a JSON card per language → printable HTML trip card + CSV log.

**Keeping the AI honest (grounding):**
- **Species** come from BirdNET, not from Gemma.
- **Conservation status, habitat and ID tips** come from the local checklist. The code overwrites any status the model tries to add, and a test checks this.
- Gemma's prompt contains **only those facts**, and it is told not to add new ones. It returns strict JSON through Ollama's `format: json` mode.
- Detections below a confidence threshold are listed as **"unsure"** and get no AI card, so the app never guesses.
- If Gemma is off or returns broken JSON, Hakki Kivi still makes a correct English card from the checklist alone.

**Swappable:** change the model with one setting (`HAKKI_MODEL=gemma4:e4b-it-qat` or any other Ollama model) and add birds for your area by editing a CSV.

## Why Does Open Innovation Matter?

- **It works where the signal doesn't.** Around Hampi and Daroji, mobile coverage drops among the boulders. BirdNET and Gemma both run on my own laptop, so the whole thing works in airplane mode. A closed cloud API simply stops working there.
- **Your location stays yours.** Bird recordings show exactly where and when you walked. With open models running locally, nothing is uploaded to a server you don't control.
- **The languages people here actually speak.** Ballari sits where Kannada, Telugu and Hindi meet. An open model trained on 140+ languages writes cards in all of them, with no per-card fees.
- **I can change how it works.** I can swap Gemma E2B for E4B on a better laptop, restrict species to a local checklist, or fine-tune later on local bird names. A closed API wouldn't let me control any of that.
- **It costs ₹0 to run.** Students, schools and village bird clubs can use it for free, forever.
- **Honest trade-off:** a large closed model would probably write richer descriptions, but it can't come with me to Daroji in airplane mode and it shouldn't hold my location history. For getting people outside, open and local is the better design.

<!-- Thanks for participating! -->
