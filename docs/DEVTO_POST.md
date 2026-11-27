---
title: "Hakki Kivi: my phone stayed in my pocket, and an offline Gemma wrote my Ballari bird walk a field card in 4 languages"
published: false
tags: devchallenge, opensource, gemma, ai
---

*This is a submission for GDG on Campus VTU Belagavi DEV Challenge 2: Touch Grass.*
<!-- Replace this line with the exact wording from the GDG template when it's shared. -->

<!-- HOOK: write 2–3 lines about Saturday morning. What did you hear first? Where were you? Phone in pocket. -->
At 6:40 on Saturday morning, a [BIRD CALL YOU HEARD] started up from the [PLACE]. My phone stayed in my pocket, recording.
Bird apps get you outside and then make you stare at them. I wanted the opposite: **walk first, screen last.**

## What I Built

**Hakki Kivi** (ಹಕ್ಕಿ ಕಿವಿ, Kannada for "Bird Ear") turns a walk's worth of bird-call recordings into a printable,
**multilingual field card**: English plus Kannada, Hindi, Telugu, Tamil and more, chosen by you.

- During the walk you record clips with the phone's normal voice recorder, in **airplane mode**, phone in your pocket.
- After the walk, **BirdNET** identifies each call on the laptop, offline.
- Each species is checked against a **local checklist** (Daroji/Hampi + common Deccan birds).
- **Gemma, running locally in Ollama**, rewrites only those checked facts as a short card in each language:
  name, one ID tip and a "listen for it next time" challenge.
- You get a one-page trip card to print and take on the next walk.

The screen time is the last two minutes of the trip, and it's the reason you go back out.

## Demo

<!-- Add: YouTube link (walk footage + airplane-mode screenshot + card being generated), a GIF, a photo of the printed card. -->
- Video: [LINK]
- Printed trip card: [PHOTO]

## Code

{% github nawazshaik313/hakki-kivi %}

## How I Built It

| Piece | Open-source part | Why |
|---|---|---|
| Bird ID | BirdNET-Analyzer | Recognises thousands of species from sound, runs on a laptop |
| Language model | Gemma 4 E2B (open weights, Apache 2.0) via Ollama | ~4.3 GB, runs on 8 GB RAM, 140+ languages |
| Facts | `ballari_checklist.csv` | Status/habitat/tips come from data, not the model |
| UI | Gradio | Opens on the phone over a hotspot with mobile data off |

**Grounding:** the prompt gives Gemma only the facts from BirdNET and the checklist, and tells it to add nothing.
The conservation status is never taken from the model: the code overwrites it from the checklist (there's a test for
this). If Gemma is off or replies with broken JSON, the app falls back to a plain English card built from the checklist.
Low-confidence detections are listed as **"unsure"** instead of being guessed.

**Speed on my laptop:** [X] seconds per card with `gemma4:e2b-it-qat` on [CPU/GPU, RAM].

## I took it outside

<!-- Fill these with your real numbers from the walk. Honest beats impressive. -->
- Where: [campus / tank / Daroji], [date], [start–end time]
- Minutes outside: **[N]** · minutes looking at a screen: **[N]**
- Clips recorded: [N] · species carded: [N] · marked unsure: [N]
- My check (`python -m hakki_kivi --eval`): **[right]/[judged] correct ([%])**

What went wrong:
- [e.g. traffic noise near the road gave low confidence]
- [e.g. one call was labelled X but it was actually Y]
- [e.g. Kannada names: N of M were good; the rest were transliterations]

## Why Does Open Innovation Matter?

- **No signal, no problem.** Around Hampi and Daroji the coverage drops, and both models run on my laptop.
- **My location stays mine.** Recordings show exactly where and when I walked. Nothing is uploaded.
- **The languages people here actually read.** One open model writes Kannada, Hindi and Telugu cards for my family and
  friends. With a closed API I'd pay per card and depend on its language support.
- **I can change it.** I can swap Gemma E2B for E4B, or fine-tune it on local bird names later.
- **Free.** Students and bird clubs can run it for ₹0.

Honest trade-off: a large closed model would probably write richer descriptions. But it can't come with me to Daroji
in airplane mode, and it shouldn't hold my location history.

## Prize Categories

<!-- List a category if the GDG template has them; otherwise delete this section. Don't leave it empty. -->
