# SycAudit — Sycophancy Auditor

SycAudit is a research-grade auditing tool that measures how much large language models bend their answers to agree with a user rather than stay truthful. It rewrites a single user prompt into multiple framing variants, collects parallel responses from several free-tier LLMs, scores each response for sycophancy using both an LLM-as-judge and a purpose-trained ML classifier, and surfaces the least sycophantic response back to the user.

Built as a lab project grounded in the UK AI Safety Institute's 2026 work on sycophancy in language models.

> ⚠️ **Status:** Active development. Architecture and scoring methodology below reflect the current design and may change as the model/response grid is finalized.

---

## Why

LLMs frequently tell users what they want to hear — agreeing with a flawed premise, reversing a correct answer under pushback, or padding responses with unwarranted validation. This is hard to detect from a single response in isolation. SycAudit's core idea: generate the *same underlying request* under several different framings, send each framing to several different models, and compare the resulting grid of responses. Sycophancy shows up as a pattern across that grid, not as a property of any one answer.

---

## How it works

```
User prompt
    │
    ▼
Prompt Variation Engine  ──▶  N framing variants (e.g. neutral, deferential,
    │                          challenging, authority-invoking, uncertain)
    ▼
Response Collection  ──▶  each variant sent to each of M LLMs (N × M grid)
    │
    ▼
Scoring Layer
    ├── LLM-as-judge: rubric-driven sycophancy score per response
    └── In-house ML classifier: five-facet rule-grounded sycophancy score
    │
    ▼
Wobble Score  ──▶  weighted combination of judge + classifier scores,
    │               measuring how much a model's answer "wobbles"
    │               across framings of the same underlying question
    ▼
Ranked results surfaced to the user, least-sycophantic response highlighted
```

### The N×M response grid

Every prompt variant is sent to every model, not one variant per model. This is deliberate: a 1-variant-to-1-model mapping would confound the effect of *framing* with the effect of *which model answered*, making results uninterpretable. The full grid lets us isolate:
- **Framing effect** — how a single model's answer shifts across variants of the same prompt
- **Model effect** — how different models respond to the same framing

### Five-facet sycophancy rubric

The in-house ML classifier scores responses against five concrete facets (grounded in the AISI paper's sycophancy taxonomy):

| Facet | What it captures |
|---|---|
| *(define facet 1)* | |
| *(define facet 2)* | |
| *(define facet 3)* | |
| *(define facet 4)* | |
| *(define facet 5)* | |

> Fill in the five facet definitions here once finalized — the judge prompt and the classifier's rule set both derive from this table, so it should be the single source of truth.

---

## Architecture

**Frontend** — React + CSS, client-side. *(details TBD — routing, state management, and component structure to be finalized)*

**Backend** — Python.

**Database** — RDBMS (PostgreSQL), storing:
- User accounts and login credentials
- Prompts and their generated variations
- LLM responses (with model name, version, and generation metadata)
- Judge scores and rationale text
- ML classifier scores per facet
- Final wobble scores

**LLM providers (free tier)** — response generation is split across multiple providers to build the model grid. Provider list and specific model versions are pinned in [`/config/models.yaml`](./config/models.yaml) *(create this file as the source of truth — provider free-tier terms and model names change frequently, so don't duplicate the list in prose here)*.

**Judge model** — a separate LLM-as-judge call scores each response against the five-facet rubric. Chosen to avoid overlap with the response-generation model pool, to limit self-preference bias.

**ML classifier** — trained in-house (scikit-learn or similar) on labeled sycophantic/non-sycophantic responses, applying the five-facet rubric as rule-grounded features.

---

## Project structure

```
sycaudit/
├── frontend/               # React app
├── backend/
│   ├── api/                 # FastAPI/Flask routes
│   ├── orchestration/       # prompt variation + parallel LLM calls
│   ├── scoring/
│   │   ├── judge.py          # LLM-as-judge scoring
│   │   └── classifier.py     # in-house ML sycophancy model
│   ├── models/               # DB models / ORM
│   └── db/                   # migrations, schema
├── ml/
│   ├── training/             # classifier training pipeline
│   └── data/                 # labeled datasets (not committed if large/private)
├── config/
│   └── models.yaml           # pinned LLM provider + model versions
├── docs/
│   └── SRS.md                # full Software Requirements Specification
└── README.md
```

## Setup

### Prerequisites
- Python 3.11+
- Node.js 18+
- PostgreSQL 15+
- API keys for the LLM providers configured in `config/models.yaml`

### Backend
```bash
cd backend
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt
cp .env.example .env       # fill in DB URL and LLM API keys
python manage.py migrate   # or your migration tool of choice
uvicorn api.main:app --reload
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```

### Environment variables
| Variable | Description |
|---|---|
| `DATABASE_URL` | PostgreSQL connection string |
| `GROQ_API_KEY` | Groq API key (free tier) |
| `GEMINI_API_KEY` | Google AI Studio / Gemini API key |
| `JUDGE_MODEL` | Model identifier used for LLM-as-judge scoring |

---

## Usage

1. Submit a prompt via the web UI.
2. SycAudit generates N framing variants automatically.
3. Each variant is sent to each configured model (N × M grid).
4. Responses are scored by the judge model and the ML classifier.
5. A wobble score is computed per model/variant, and the least sycophantic response is returned to the user, alongside the full scoring breakdown for transparency.

---

## Research grounding

This project's sycophancy definitions and evaluation approach are based on:
- UK AI Safety Institute, 2026 — sycophancy in language models *(add full citation)*

---

## Team

Ishika Bhute
Soumitra Rajguru

## License

*(choose a license — MIT is a reasonable default for a lab/research project)*
