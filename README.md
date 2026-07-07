# CaptionCraft

**AI-Powered Video Captioning in 4 Stylistic Voices**

> Built for the **AMD Developer Hackathon: ACT II** — a hands-on event exploring AI agents, intelligent workflows, and real AI applications on AMD AI Developer Cloud, ROCm, and Fireworks AI.

Upload a video and get instant AI-generated captions in multiple tones — Formal, Sarcastic, Tech Humor & Non-Tech — powered by Qwen3 Omni on Fireworks AI.

## Features

- **Upload & Go** — drag-and-drop video upload (MP4, MOV, WebM, AVI, MKV; up to 25 MB)
- **4 Unique Voices** — pick one or all; get captions tailored to each style
- **Smart Preview** — inline video player with file info
- **Copy & Download** — copy individual captions or download all as JSON
- **Dark & Dreamy UI** — animated beam background, glassmorphism cards, Tailwind CSS 4

## About the Hackathon

The **AMD Developer Hackathon: ACT II** is a hands-on event for developers, founders, engineers, and builders who want to push what's possible with AI on real infrastructure. At the center of it: **AI Agents** — a space to explore intelligent workflows, automation, and real AI applications. Whether you're just starting out or already building, you can jump in and start creating.

This project was built using **AMD AI Developer Cloud**, **ROCm**, and the **Fireworks AI API** — all fully in the cloud, so developers can focus on building instead of setup.

## Architecture

```
┌──────────────────┐     POST /api/caption     ┌──────────────────┐     Fireworks AI API     ┌──────────────┐
│  React 19 + Vite │  ──────────────────────▶  │  FastAPI Backend │  ──────────────────────▶  │  Qwen3 Omni  │
│  Tailwind CSS 4  │  ◀──────────────────────  │  (Python 3.11+)  │  ◀──────────────────────  │   (30B A3B)   │
│  (frontend/)     │      JSON response        │  (backend/)      │       Captions + Summary  │              │
└──────────────────┘                           └──────────────────┘                           └──────────────┘
```

## The Four Voices

| Style | Tone | Example Vibe |
|-------|------|-------------|
| **Formal** | Professional, factual, neutral | "A person demonstrates a cooking technique..." |
| **Sarcastic** | Dry wit, irony, understatement | "Oh great, another 'life hack' that takes 47 steps..." |
| **Tech Humor** | Geeky, programming jargon, metaphors | "This video has more runtime errors than my Monday morning..." |
| **Non-Tech** | Relatable, punny, everyday humor | "Me trying to look productive while doing absolutely nothing..." |

## Getting Started

### Prerequisites
- Python 3.11+
- Node.js 20+
- A [Fireworks AI](https://fireworks.ai) API key

### 1. Clone & Setup Backend
```bash
git clone https://github.com/balajireddy2480-beep/CaptionCraft.git
cd CaptionCraft
cp .env.example .env   # Add your FIREWORKS_API_KEY
python -m venv .venv
.venv\Scripts\activate   # Windows
pip install -r requirements.txt
uvicorn backend.main:app --reload --port 8000
```

### 2. Setup Frontend
```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173` — the Vite dev server proxies API calls to port 8000.

### 3. Build for Production
```bash
cd frontend && npm run build
```
The backend auto-serves `frontend/dist/` when it exists.

## Project Structure

```
CaptionCraft/
├── backend/
│   ├── main.py                  # FastAPI app entry
│   ├── config.py                # Environment config
│   ├── models/schemas.py        # Pydantic models
│   ├── routers/caption.py       # API endpoint
│   ├── services/
│   │   ├── fireworks_service.py # Fireworks AI client
│   │   └── prompt_builder.py    # Style-specific prompts
│   └── utils/validators.py      # File validation
├── frontend/
│   ├── src/
│   │   ├── App.jsx              # Root component
│   │   ├── components/          # UI components
│   │   ├── hooks/               # useUpload, useCaptions
│   │   ├── services/api.js      # API client
│   │   └── utils/               # Constants, helpers
│   ├── index.html
│   ├── package.json
│   └── vite.config.js
├── .env.example
├── .gitignore
└── requirements.txt
```

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `FIREWORKS_API_KEY` | — | Fireworks AI API key (required) |
| `FIREWORKS_MODEL` | `qwen3-omni-30b-a3b-instruct` | Model for captioning |
| `MAX_VIDEO_SIZE_MB` | `25` | Maximum upload file size |
| `ALLOWED_EXTENSIONS` | `.mp4,.mov,.avi,.webm,.mkv` | Accepted file types |

## Built With

**Frontend:** React 19, Vite 6, Tailwind CSS 4, Framer Motion (`motion`), TypeScript  
**Backend:** Python 3.11+, FastAPI, Pydantic, OpenAI SDK  
**AI:** Qwen3 Omni 30B via Fireworks AI on AMD AI Developer Cloud + ROCm
