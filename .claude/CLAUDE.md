# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

PhishGuard Pro is an AI-powered Active Defense system against phishing. It engages attackers in believable conversation, wastes their time (tarpitting), and extracts Indicators of Compromise (IOCs: crypto wallets, IBANs, phone numbers, URLs).

## Architecture

**Monorepo with three main components:**

- **frontend/** - Next.js 16 (React 19, Tailwind CSS v4, shadcn/ui, Vercel AI SDK)
- **backend/** - FastAPI with LangGraph orchestration, LangChain-OpenAI, Pydantic
- **supabase/** - Database migrations (Postgres with RLS, pgvector for RAG)

**Agent Workflow (LangGraph):**
```
Email → Profiler → Persona Selection → [Conversation Loop] → Summary
                                              ↑
                        Scammer message → Intel Extraction
                                              |
                         Human approval ← Safety Check
```

Four specialized agents: Profiler (classifies attack type), Persona Engine (generates victim persona), Conversation Agent (generates responses), Intel Collector (regex-based IOC extraction).

## Development Commands

### Frontend (from `frontend/`)
```bash
npm install          # Install dependencies
npm run dev          # Start dev server (http://localhost:3000)
npm run build        # Production build
npm run lint         # ESLint
npm run test         # Vitest unit tests
npm run test:coverage
npm run test:e2e     # Playwright E2E tests
npm run test:e2e:ui  # Playwright with UI
```

### Backend (from `backend/`)
```bash
uv sync              # Install dependencies
uv run uvicorn src.phishguard.main:app --reload --port 8000  # Start dev server
uv run pytest -v     # Run tests
uv run pytest tests/path/test_file.py::test_function  # Single test
uv run ruff check .  # Lint
uv run ruff format . # Format
```

### Database
```bash
supabase db push     # Apply migrations
```

## Key Technical Decisions

- **LangGraph over LangChain Agents**: Required for stateful cycles, human-in-the-loop approval, and checkpoint persistence
- **Vercel AI SDK**: SSE bridge between Python backend and React frontend for streaming
- **Faker library**: Seeded per-session for consistent fake persona data
- **Safety layer**: Bidirectional validation (input sanitization + output blocking of real PII)

## Database Schema

- `sessions` - Phishing simulation sessions (user_id, attack_type, persona, status)
- `messages` - Conversation history (role: 'user'|'assistant'|'scammer')
- `ioc_extracted` - Extracted IOCs (type: 'iban'|'btc'|'url'|'phone', confidence)

All tables use Row Level Security (RLS).

## Testing Strategy

- **Backend**: pytest with pytest-asyncio, fixtures for mocking, parameterized tests
- **Frontend Unit**: Vitest with jsdom, @testing-library/react
- **Frontend E2E**: Playwright

Tests follow AAA pattern (Arrange-Act-Assert). Coverage focuses on critical business logic.
