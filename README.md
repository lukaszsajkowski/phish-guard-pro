# PhishGuard Pro

AI-Powered Active Defense Against Phishing Attacks.

PhishGuard Pro is an autonomous agent-based system that implements the Active Defense paradigm against phishing. It engages attackers in believable conversation, wastes their time, and extracts valuable Indicators of Compromise (IOC).

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        PhishGuard Pro                           │
├─────────────────────────────────────────────────────────────────┤
│  Frontend (Next.js 16)  │  Backend (FastAPI)  │  Database       │
│  - React 19             │  - LangGraph        │  - Supabase     │
│  - Tailwind CSS v4      │  - OpenAI           │  - Postgres     │
│  - shadcn/ui            │  - Faker            │  - RLS          │
│  - Vercel AI SDK        │  - Pydantic         │  - Auth         │
└─────────────────────────────────────────────────────────────────┘
```

## Project Structure

```
phish-guard-pro/
├── frontend/              # Next.js 16 Frontend
│   ├── src/
│   │   ├── app/           # App Router pages
│   │   ├── components/    # React components
│   │   ├── lib/           # Utilities (Supabase client)
│   │   └── types/         # TypeScript types
│   └── package.json
├── backend/               # FastAPI Backend
│   ├── src/phishguard/
│   │   ├── api/           # API routes
│   │   ├── core/          # Configuration
│   │   └── main.py        # Application entry
│   ├── tests/
│   └── pyproject.toml
├── supabase/              # Database Migrations
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

## Database Schema

| Table | Purpose |
|-------|---------|
| `sessions` | Phishing simulation sessions |
| `messages` | Conversation history |
| `ioc_extracted` | Extracted threat indicators |

All tables use Row Level Security (RLS) to ensure users can only access their own data.

## Testing

### Backend Tests

```bash
cd backend
uv run pytest -v
```

### Frontend Type Check

```bash
cd frontend
npm run build
```

## License

MIT License - Built for security researchers.
