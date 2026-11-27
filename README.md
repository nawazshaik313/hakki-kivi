# 🐦 Hakki Kivi (ಹಕ್ಕಿ ಕಿವಿ, "Bird Ear")

**Walk first, screen last.** Record bird calls on a walk with your phone in your pocket. When you get back,
Hakki Kivi identifies the birds with **BirdNET** and has **Gemma**, running locally in **Ollama**, write a short
**multilingual field card** for each one: English plus Kannada, Hindi, Telugu, Tamil, Malayalam, Marathi
and more. You print the card and take it on the next walk.

No internet, no account, no API key, no cost. Built for the GDG on Campus VTU Belagavi **DEV Challenge 2: "Touch Grass"**
(build with open-source AI and get people outside).

```
 phone voice recorder        laptop (offline)
 (airplane mode, pocket) ──► BirdNET (open source)          ──► top species + confidence per clip
                              │
                              ▼
                             local checklist (Ballari/Daroji)  ──► status, habitat, ID tip  (facts)
                              │
                              ▼
                             Gemma 4 E2B in Ollama (open weights) ──► the facts rewritten in N languages
                              │
                              ▼
                             printable trip card (HTML/PDF) + walk log CSV + honest eval
```

## Why open source matters here

- **Works where there's no signal.** The rocky Hampi–Daroji country near Ballari (a BirdLife Important Bird Area)
  has patchy coverage. BirdNET and Gemma both run on the laptop, so nothing needs the network.
- **Your location stays with you.** Bird recordings carry where and when you walked. Nothing leaves your machine.
- **Many languages, free.** An open model trained on 140+ languages writes cards in the language your bird club,
  family or village actually reads. You can swap or fine-tune the model whenever you want.
- **Grounded, not invented.** Species come from BirdNET, and conservation status, habitat and the ID tip come from the
  local checklist. Gemma only rewrites those facts in each language. If Gemma isn't running, you still get a correct
  English card built from the checklist alone.

## Quick start (Windows, macOS, Linux)

1. **Install Ollama** from https://ollama.com and pull an open Gemma model:
   ```bash
   ollama pull gemma4:e2b-it-qat      # ~4.3 GB, fine on 8 GB RAM
   # 16 GB RAM / GPU:  ollama pull gemma4:e4b-it-qat
   ```
   Any Ollama model tag works. Set it with `HAKKI_MODEL` or `--model`.
2. **Python 3.11–3.13** and dependencies:
   ```bash
   python -m venv .venv
   .venv\Scripts\activate            # Windows   (macOS/Linux: source .venv/bin/activate)
   pip install -r requirements.txt
   ```
   For `.m4a` recordings from a phone, install **ffmpeg** and put it on PATH, or record in WAV.
3. **Try it without recordings** (uses saved demo detections):
   ```bash
   python -m hakki_kivi --demo samples/demo_detections.json --lang kn hi te --name "Demo walk"
   ```
4. **Run it on your walk:**
   ```bash
   python -m hakki_kivi path/to/walk_clips/ --lang kn hi --name "Daroji, Saturday" --lat 15.25 --lon 76.55
   ```
5. **Or use the app:** `python -m hakki_kivi.app`, then open http://localhost:7860.

### Use it from the phone with no internet at all
Turn on the phone's hotspot with **mobile data off**, connect the laptop to it, then run:
```bash
set HAKKI_SHARE_LAN=1          # Windows  (macOS/Linux: export HAKKI_SHARE_LAN=1)
python -m hakki_kivi.app
```
Open `http://<laptop-ip>:7860` on the phone.

## On the walk
1. Phone in **airplane mode**, in your pocket. Open the voice recorder.
2. When you hear a bird, stop and record 30–60 s. Say the place out loud at the start of the clip.
3. Back home, drop all the clips into the app and press **Make my trip card**.
4. Print the card. Next walk, try to *see* each bird it lists.

## Check it honestly
Every run writes `trips/trip-*.csv`. Fill the last column with `right` / `wrong` / `unsure`
(compare with what you saw, a photo, or a birder friend), then run:
```bash
python -m hakki_kivi --eval trips/trip-XXXX.csv
```
You get the hit rate and a list of detections that aren't on the local checklist.

## Settings (environment variables)
| Variable | Default | Meaning |
|---|---|---|
| `HAKKI_MODEL` | `gemma4:e2b-it-qat` | Ollama model tag |
| `HAKKI_OLLAMA_URL` | `http://localhost:11434` | Ollama server |
| `HAKKI_LAT` / `HAKKI_LON` | `15.14` / `76.92` (Ballari) | Location for BirdNET's species filter |
| `HAKKI_MIN_CONF` | `0.5` | Below this, a detection is listed as "unsure" and gets no card |
| `HAKKI_CHECKLIST` | `data/ballari_checklist.csv` | Your local checklist |

## The checklist
`data/ballari_checklist.csv` is a **starter list**: the threatened species reported for Daroji Sloth Bear Sanctuary in
*Journal of Threatened Taxa* article 6855 (189 species recorded), plus widespread Deccan birds. Statuses marked "as reported" come from that
paper, so check the current IUCN Red List before you quote them. Add rows for your area (columns: `common_name`,
`scientific_name`, `status`, `habitat`, `id_tip`, `source`). Use the scientific names BirdNET outputs.

## Tests
```bash
pytest
```
The tests run with no BirdNET, Ollama or internet. They include an HTTP test against a fake Ollama server and a check
that the model can never override the conservation status.

## Credits and licenses
- Code: MIT (this repo).
- **BirdNET-Analyzer**, K. Lisa Yang Center for Conservation Bioacoustics & Chemnitz University of Technology: code MIT.
  The model weights have their own license (newer models Apache 2.0, older models CC BY-NC-SA 4.0, non-commercial).
  See the BirdNET-Analyzer README for the model you install.
- **Gemma 4**, Google DeepMind: open weights, Apache 2.0. Served locally with **Ollama** (MIT).
- **Gradio** (Apache 2.0).
- Daroji species information: *Journal of Threatened Taxa*, article 6855.

Built by Shaik Mohammed Nawaz, AI & ML, Ballari Institute of Technology and Management.
