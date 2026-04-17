# 💬 SpeakAgain — AI-powered Aphasia Communication & Rehabilitation Aid

**Project #6 of 10** in the Neurological Rehabilitation AI Series by **Samuel Oluwakoya**
A computer science graduate, foot drop patient, and independent AI health researcher based in Lagos, Nigeria building open-source AI tools for stroke rehabilitation.

**Contact:** samueloluwakoyat@gmail.com
**GitHub:** github.com/samexdgs
**Live series app #1:** fdmapp.streamlit.app

---

## The problem

Aphasia affects roughly 1 in 3 stroke survivors — about 5 million new cases globally every year. The person knows what they want to say but cannot produce the words. Speech-language therapy is the evidence-based treatment, but:

- In sub-Saharan Africa, speech-language therapists are scarce and expensive
- Intensity matters most (Cochrane Review, 2016) — 10+ hours/week is effective, but unavailable
- Family caregivers receive no tools or training
- Patients lose confidence, withdraw socially, and decline faster

SpeakAgain addresses this gap directly.

---

## What it does

Two modes, one app:

**Communication mode** — Patient types 1–5 word fragments. The AI builds 3 complete sentence options, ranks them by confidence, and reads them aloud. Crisis keywords ("pain", "fall", "chest") trigger an automatic email alert to the caregiver.

**Rehabilitation mode** — Daily structured exercises personalised to the patient's aphasia type (Broca's / Wernicke's / Global / Anomic / Conduction) and severity score. Six exercise types grounded in published aphasia therapy evidence:
- Word retrieval with graded cueing (picture-naming)
- Sentence building (drag-and-drop word ordering)
- Cloze completion (fill-in-the-blank)
- Reading comprehension (progressive difficulty)
- Repetition (audio-to-text)
- Progressive naming therapy

---

## Evidence base

This tool is grounded in the following research:

| Study | Finding |
|---|---|
| Kim et al., 2025 (JMIR mHealth) — VoiceAdapt RCT | App-based naming therapy produces measurable gains in chronic aphasia |
| Braley et al., 2021 (Frontiers in Neurology) | Digital therapeutic improved WAB-AQ scores by 6.4 points vs workbook |
| Upton et al., 2024 — iTalkBetter | +4.4 informative words in spontaneous speech, maintained at 12 weeks |
| Ericson et al., 2025 — Systematic review | 39 studies unanimously found computer therapy effective for trained items |
| Brady et al., Cochrane Review 2016 | Therapy intensity is the strongest predictor of recovery |
| Breitenstein et al., 2017 (Lancet) | 10+ hrs/week intensive SLT improves outcomes in chronic aphasia |

---

## Features

### 1. AI sentence completion engine
- Fragment-to-sentence: 1–5 words → 3 complete sentences with confidence scores
- Predictive word suggestions as you type
- Context memory (last 10 exchanges improve suggestions)
- Voice output via browser TTS (gTTS)
- **Works offline** — rule-based fallback when AI unavailable

### 2. Aphasia classification
- 8-task assessment adapted from WAB-R principles
- Classifies type: Broca's, Wernicke's, Global, Anomic, Conduction, Mild
- Severity score 0–5
- Monthly reassessment tracks improvement

### 3. Personalised daily therapy
- 6 exercise types, 4 difficulty levels
- Adapts to severity score automatically
- Progressive hint system (letter → partial word → full word)
- Daily streak tracking

### 4. Caregiver bridge (Brevo integration)
- Daily summary emails with phrases communicated, exercises done, mood trend
- Crisis alerts — pain/fall/chest keywords trigger immediate email
- Milestone celebrations when severity score improves
- Custom family-specific phrase library
- 200+ pre-built phrases across 8 categories

### 5. Progress dashboard
- Severity score line chart (monthly)
- Exercise breakdown by type
- Recovered words list (words patient couldn't say → can now)
- GitHub-style practice calendar

### 6. Accessibility
- Multilingual phrase library: **Yoruba, Igbo, Hausa, Pidgin, English**
- Large text mode
- Left-hand mode (for right-hemiplegia patients)
- Session pause/resume

---

## Tech stack

| Layer | Tool | Why |
|---|---|---|
| Frontend | Streamlit | Rapid deploy, consistent with series (fdmapp) |
| AI | Claude API (claude-sonnet-4-6) | Best-in-class fragment understanding |
| Offline AI | Rule-based patterns | Zero dependency, always works |
| TTS | gTTS | Free, browser-playable MP3 |
| Email | **Brevo REST API** | 300 emails/day free, 99% deliverability |
| Data | Streamlit session state | Simple for MVP; moves to Supabase for production |
| Charts | Plotly | Interactive, accessible |

---

## File structure

```
speakagain/
├── app.py                  # Main Streamlit app
├── clinical_data.py        # Aphasia types, phrases, exercises, crisis detection
├── ai_completion.py        # Claude API + rule-based fallback
├── brevo_mailer.py         # Email templates + Brevo REST API calls
├── requirements.txt        # Python dependencies
├── .streamlit/
│   ├── config.toml         # Theme + server config
│   └── secrets.toml.example # Template for API keys
└── README.md               # This file
```

**Novelty:** First open-source aphasia communication tool built specifically for low-resource African settings, with Yoruba/Igbo/Hausa support, evidence-based exercise protocols, and caregiver bridge architecture.

---

## Disclaimer

SpeakAgain is a research and accessibility tool. It has **not** been validated as a medical device and does **not** replace professional speech-language therapy. The AI sentence completion and aphasia severity scoring are designed as assistive aids, not clinical diagnostics. Always follow the guidance of a qualified speech-language therapist where accessible. In a medical emergency, contact emergency services immediately.

---

Built by **Samuel Oluwakoya** — Computer Science Graduate, Foot Drop Patient, AI Health Researcher
Lagos, Nigeria · samueloluwakoyat@gmail.com · github.com/samexdgs
