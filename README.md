# NATIVE 2.0 — Voice-Based English Learning Agent

> **Microsoft Agents League Hackathon 2026 — Reasoning Agents Track**
> Built with Microsoft Foundry IQ · Azure Voice Live · Azure Speech · Azure AI Foundry

---

## The Problem

Language learning apps teach grammar. Real life requires conversation. These are different things.

Duolingo gives you exercises. Rosetta Stone gives you repetition. Neither gives you a real conversation with a human-like partner who listens, responds, and adapts to your mistakes in real time.

**NATIVE** is not a language app. It is a social immersion environment where learning happens as a natural consequence of interaction — exactly how languages are learned in real life.

---

## What NATIVE Does

NATIVE is a voice-first AI agent that holds real, fluid English conversations with Spanish speakers. It:

- **Listens and responds in real time** — no turn-taking, no waiting, natural interruptions supported
- **Detects pronunciation errors** word by word and highlights them with color in real time
- **Corrects naturally** — like a native speaker friend would, never like an academic teacher
- **Adapts to your level** — from A1 beginner to C1 advanced, the system detects and adjusts
- **Remembers your patterns** — recurring errors get worked into future conversations deliberately
- **Shows you the translation** — Spanish subtitles appear for lower-level users, fade as they improve
- **Summarizes each session** — level detected, achievements, areas to improve

---

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                   NATIVE 2.0                         │
│                                                       │
│  React Frontend                                       │
│  ├── Particle Orb (Three.js)                         │
│  ├── Real-time transcript display                    │
│  ├── Pronunciation color coding                      │
│  ├── Spanish subtitle translation                    │
│  └── Session summary screen                          │
│                          │                           │
│                    WebSocket                         │
│                          │                           │
│  FastAPI Backend                                     │
│  ├── JWT Authentication                              │
│  ├── Azure Voice Live WebSocket bridge               │
│  ├── Pronunciation Assessment (parallel stream)      │
│  ├── Azure Translator (real-time subtitles)          │
│  ├── Pedagogical injection (every N turns)           │
│  └── Session summary generation                      │
│                          │                           │
│  SQLite Database                                     │
│  ├── Users & sessions                                │
│  ├── Error patterns per user                         │
│  ├── Pronunciation scores history                    │
│  └── Session summaries                               │
└─────────────────────────────────────────────────────┘

Microsoft Foundry IQ Services:
├── Azure Voice Live API (GPT-4o Mini)  → conversational pipeline
├── Azure Speech Services               → pronunciation assessment
├── Azure AI Translator                 → real-time subtitles
└── Grok-4.3 via Azure AI Foundry      → pedagogical analysis
```

---

## Multi-Step Reasoning

NATIVE demonstrates clear multi-step reasoning across every conversation turn:

**Step 1** → Azure Voice Live receives audio from the user in real time
**Step 2** → Speech-to-text transcription runs inside the Voice Live pipeline
**Step 3** → Pronunciation Assessment runs in parallel on the same audio stream
**Step 4** → Word-level accuracy scores determine color coding sent to the frontend
**Step 5** → Azure Translator generates Spanish subtitles adapted to user level
**Step 6** → Every 5 turns, the system injects pedagogical corrections based on error patterns
**Step 7** → At session end, level is recalculated and a personalized summary is generated

---

## Characters

NATIVE offers three distinct personalities, each with a Dragon HD neural voice:

| Character | Voice | Personality |
|-----------|-------|-------------|
| **Ava** | en-US-Ava:DragonHDLatestNeural | Warm, expressive, loves deep conversations |
| **Emma** | en-US-Emma:DragonHDLatestNeural | Direct, witty, works in tech |
| **Andrew** | en-US-Andrew:DragonHDLatestNeural | Confident, natural, sports journalist |

Each character responds differently to user tone — friendly, sarcastic, rude, or shy — making conversations feel genuinely social rather than scripted.

---

## Level System

NATIVE automatically detects and adapts to user level:

| Level | Description | Character Behavior |
|-------|-------------|-------------------|
| A1 | Complete beginner | Max 5-word sentences, very common vocabulary |
| A2 | Elementary | Short clear sentences, basic grammar focus |
| B1 | Intermediate | Natural vocabulary, occasional corrections |
| B2 | Upper intermediate | Rich vocabulary, subtle corrections only |
| C1 | Advanced | Native-speed conversation, minimal intervention |

Level is recalculated after each session based on Pronunciation Assessment scores.

---

## Natural Correction Philosophy

NATIVE never says "you should say" or "the correct form is."

Instead, characters integrate corrections naturally:

> User: "Yesterday I go to the park"
> Ava: "Oh you went to the park? What did you do there?"

The correct form appears in the response. The user hears it. Learning happens without interruption.

---

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Conversational pipeline | Azure Voice Live API (GPT-4o Mini) |
| Speech-to-text | Azure Voice Live (integrated) |
| Pronunciation Assessment | Azure Speech Services SDK |
| Translation | Azure AI Translator |
| LLM analysis | Grok-4.3 via Azure AI Foundry |
| Backend | Python · FastAPI · WebSocket |
| Frontend | React · Vite · TailwindCSS · Three.js |
| Database | SQLite |
| Auth | JWT |

---

## Foundry IQ Knowledge Base — Pending

NATIVE 2.0 includes a pedagogical knowledge base designed for Foundry IQ integration with 4 documents covering:
- English grammar rules for Spanish speakers (`knowledge/01_grammar_rules.md`)
- Pronunciation guide (`knowledge/02_pronunciation_guide.md`)
- Vocabulary by level A1-C1 (`knowledge/03_vocabulary_by_level.md`)
- Idioms and conversational expressions (`knowledge/04_idioms_conversational.md`)

The integration code is implemented in `src/foundry_iq.py` and connected to the pedagogical injection system in `src/pedagogy.py`. Full Foundry IQ integration with Azure AI Search is pending due to embedding model quota limitations on the Azure free tier.

**Status:** Knowledge base documents ✅ | Azure AI Search resource ✅ | Embedding quota pending ⏳

---

## Project Structure

```
Native-fullstack/
├── Native-backend/
│   ├── src/
│   │   ├── api.py              → FastAPI + JWT + WebSocket
│   │   ├── voice_live.py       → Voice Live pipeline
│   │   ├── pronunciation.py    → Pronunciation Assessment
│   │   ├── translator.py       → Azure Translator
│   │   ├── pedagogy.py         → Pedagogical injection
│   │   ├── foundry_iq.py       → Foundry IQ integration
│   │   ├── level_detector.py   → Level detection A1-C1
│   │   ├── context_builder.py  → RAG user context
│   │   └── database.py         → SQLite
│   ├── knowledge/              → Foundry IQ documents
│   ├── .env.example
│   └── requirements.txt
└── native-frontend/
    └── src/
        ├── components/
        │   ├── Login.jsx
        │   ├── Session.jsx
        │   └── Orb.jsx
        └── App.jsx
```

---

## Setup

### Prerequisites

- Python 3.11+
- Node.js 18+
- Azure subscription with:
  - Azure AI Foundry project
  - Azure Speech Service
  - Azure Voice Live API access

### Backend

```bash
cd Native-backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Fill in your Azure credentials in .env
uvicorn src.api:app --reload --port 8000
```

### Frontend

```bash
cd native-frontend
npm install
npm run dev
```

Open `http://localhost:5173`

---

## Demo

1. Register an account
2. Choose your conversation partner (Ava, Emma, or Andrew)
3. Start speaking in English
4. Watch your words appear with pronunciation color coding
5. See Spanish subtitles appear below the character's response
6. End the session to see your level and personalized summary

---

## Category

**Reasoning Agents** — Microsoft Foundry IQ

NATIVE uses Azure AI Foundry as its intelligence layer for multi-step reasoning across conversation, pronunciation analysis, pedagogical injection, and adaptive level detection.

---

## Author

**Nicolas Zorrilla** · [@ncodexz](https://github.com/ncodexz)

*Built for the Microsoft Agents League Hackathon 2026*