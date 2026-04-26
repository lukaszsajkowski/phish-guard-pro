# PhishGuard Pro

AI-Powered Active Defense Against Phishing Attacks.

PhishGuard Pro is an autonomous agent-based system that implements the Active Defense paradigm against phishing. It engages attackers in believable conversation, wastes their time (tarpitting), and extracts valuable Indicators of Compromise (IOCs) such as crypto wallets, IBANs, phone numbers, URLs, and IP addresses.

## Architecture

```
┌──────────────────────────────────────────────────────────────────────┐
│                          PhishGuard Pro                              │
├──────────────────────────────────────────────────────────────────────┤
│  Frontend (Next.js 16)   │  Backend (FastAPI)    │  Database         │
│  - React 19              │  - LangGraph          │  - Supabase       │
│  - Tailwind CSS v4       │  - LangChain-OpenAI   │  - Postgres       │
│  - shadcn/ui             │  - Faker              │  - RLS            │
│  - Vercel AI SDK         │  - Pydantic v2        │  - Auth           │
│  - next-themes           │  - phonenumbers       │  - pgvector       │
└──────────────────────────────────────────────────────────────────────┘
```

### Agent Workflow (LangGraph)

```
Email → Profiler → Persona Selection → [Conversation Loop] → Summary
                                              ↑
                        Scammer message → Intel Extraction
                                              |
                         Human approval ← Safety Check
```

Four specialized agents orchestrated by LangGraph:

- **Profiler** - Classifies attack type (Nigerian 419, Romance Scam, Tech Support, etc.) and assesses risk
- **Persona Engine** - Generates a believable victim persona using Faker (seeded per-session for consistency)
- **Conversation Agent** - Produces victim responses that keep the attacker engaged
- **Intel Collector** - Regex-based IOC extraction (BTC wallets, IBANs, URLs, phone numbers, IPs)

### IOC Enrichment Pipeline

Extracted IOCs are enriched via external threat intelligence sources:

- **VirusTotal** - URL and domain reputation
- **AbuseIPDB** - IP address abuse reports
- **NumVerify** - Phone number validation and carrier lookup
- **Blockchain Explorer** - Bitcoin wallet transaction history

## Project Structure

```
phish-guard-pro/
├── frontend/                  # Next.js 16 Frontend
│   ├── src/
│   │   ├── app/               # App Router pages (dashboard, history, auth)
│   │   ├── components/
│   │   │   ├── ui/            # shadcn/ui primitives
│   │   │   ├── app/           # Layout, sidebar, theme toggle
│   │   │   ├── dashboard/     # Chat, intel panel, risk score, persona
│   │   │   └── history/       # Session list, detail view, pagination
│   │   ├── hooks/             # useEnrichment, useApiWithRetry, useMediaQuery
│   │   ├── lib/               # Supabase client, utils, constants
│   │   └── types/             # TypeScript schemas & database types
│   └── package.json
├── backend/                   # FastAPI Backend
│   ├── src/phishguard/
│   │   ├── agents/            # Profiler, Persona, Conversation, Intel Collector
│   │   ├── analyzers/         # Urgency & personalization risk analyzers
│   │   ├── api/routers/       # REST endpoints (7 route modules)
│   │   ├── models/            # Pydantic v2 schemas
│   │   ├── orchestrator/      # LangGraph workflow (graph, nodes, state)
│   │   ├── safety/            # Output validator, unmasking detector
│   │   ├── services/          # Enrichment, risk scoring, session management
│   │   │   └── sources/       # VirusTotal, AbuseIPDB, BTC, phone enrichment
│   │   ├── llm/               # LLM client wrapper
│   │   └── main.py            # Application entry
│   ├── tests/
│   └── pyproject.toml
├── supabase/                  # Database Migrations
│   └── migrations/
└── README.md
```

## Prerequisites

- **Node.js 20+** - For the Next.js frontend
- **Python 3.12+** - For the FastAPI backend
- **Supabase CLI** - For database migrations (`brew install supabase/tap/supabase`)
- **uv** (recommended) or pip - For Python dependency management

## Quick Start

### 1. Clone and Setup Environment

```bash
# Copy environment files
cp frontend/.env.example frontend/.env.local
cp backend/.env.example backend/.env
```

### 2. Configure Supabase

1. Create a new project at [supabase.com](https://supabase.com)
2. Copy your project URL and keys to the env files
3. Initialize Supabase locally:

```bash
supabase init
supabase link --project-ref YOUR_PROJECT_REF
supabase db push
```

### 3. Start Frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend will be available at http://localhost:3000

### 4. Start Backend

```bash
cd backend

# Using uv (recommended)
uv sync
uv run uvicorn src.phishguard.main:app --reload --port 8000

# Or using pip
pip install -e ".[dev]"
uvicorn src.phishguard.main:app --reload --port 8000
```

Backend API will be available at http://localhost:8000
API docs at http://localhost:8000/docs (in debug mode)

## Environment Variables

### Frontend (`frontend/.env.local`)

| Variable | Description |
|----------|-------------|
| `NEXT_PUBLIC_SUPABASE_URL` | Supabase project URL |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | Supabase anonymous key |
| `NEXT_PUBLIC_API_URL` | Backend API URL |

### Backend (`backend/.env`)

| Variable | Description |
|----------|-------------|
| `SUPABASE_URL` | Supabase project URL |
| `SUPABASE_SERVICE_ROLE_KEY` | Supabase service role key (server-side only) |
| `OPENAI_API_KEY` | OpenAI API key for LLM |
| `OPENAI_PRIMARY_MODEL` | Primary model (default: gpt-4o) |
| `OPENAI_FALLBACK_MODEL` | Fallback model (default: gpt-4o-mini) |
| `VIRUSTOTAL_API_KEY` | VirusTotal API key (optional, for URL/domain enrichment) |
| `ABUSEIPDB_API_KEY` | AbuseIPDB API key (optional, for IP enrichment) |
| `NUMVERIFY_API_KEY` | NumVerify API key (optional, for phone enrichment) |

## Database Schema

| Table | Purpose |
|-------|---------|
| `sessions` | Phishing simulation sessions (attack type, persona, status, turn limit) |
| `messages` | Conversation history (role: user/assistant/scammer) |
| `ioc_extracted` | Extracted IOCs (types: iban, btc, url, phone, ip; with confidence) |
| `ioc_enrichment` | Enrichment data from external threat intel sources |

All tables use Row Level Security (RLS) to ensure users can only access their own data.

## Testing

### Backend

```bash
cd backend
uv run pytest -v                 # All tests
uv run ruff check .              # Lint
uv run ruff format --check .     # Format check
```

### Frontend

```bash
cd frontend
npm run test                     # Vitest unit tests
npm run test:coverage            # With coverage
npm run lint                     # ESLint
npm run build                    # Type check via production build
npm run test:e2e                 # Playwright E2E tests
npm run test:e2e:ui              # Playwright with interactive UI
```

## License

MIT License - Built for security researchers.
