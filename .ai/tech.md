# Tech Stack - PhishGuard

## Overview

Enterprise-grade stack optimized for SaaS deployment, persistence, and complex agent orchestration.

## Components

| Component     | Technology               | Justification                           |
| ------------- | ------------------------ | --------------------------------------- |
| Orchestration | LangGraph                | Stateful cycles, human-in-the-loop      |
| LLM Primary   | GPT-5.1                  | Best quality/cost for chat              |
| LLM Fallback  | GPT-4o-mini              | Cost; graceful degradation              |
| Backend API   | FastAPI (Python 3.12+)   | Async I/O, Pydantic, SSE streaming      |
| Frontend      | Next.js 16+ (React)      | SaaS standard, full UI customization    |
| Database      | Supabase (Postgres)      | Persistence, RLS, pgvector for RAG      |
| Auth          | Supabase Auth            | JWT, OAuth, Row Level Security          |
| AI Streaming  | Vercel AI SDK            | SSE bridge between Python and React     |
| Fake Data     | Faker library            | Seeded per-session                      |
| Safety Layer  | Regex + blocklist        | Bidirectional validation                |
| Export        | Native Python JSON/CSV   | No external deps needed                 |

## Architecture Decision: Why LangGraph

The workflow requires:

1. **Stateful Cycles**: The conversation loop needs persistent state across turns.
2. **Human-in-the-loop**: User approval of agent responses before finalization.
3. **Persistence**: Save graph state to database for session resumption.

```text
Email -> Profiler -> Persona Selection -> [Conversation Loop] -> Summary
                                                 ^
                           Scammer message -> Intel Extraction
                                                 |
                            Human approval <- Safety Check
```

LangGraph provides:

- Native checkpointing (PostgresCheckpointer via Supabase)
- Interrupt/resume for human approval workflows
- Conditional edges for safety re-generation loops
- Graph visualization for debugging

## Safety Architecture

The safety layer operates bidirectionally:

### Input Sanitization (Scammer Messages)

- Prevents prompt injection attacks
- Strips potentially malicious formatting
- Validates character limits (1-50,000 chars per PRD)

### Output Validation (Agent Responses)

- Blocks real PII formats (SSN, national ID patterns)
- Blocks real corporate domains from blocklist
- Blocks sensitive financial data formats
- Auto-regenerates response on unsafe content detection

## LLM Usage Strategy

| Agent              | Model           | Rationale                          |
| ------------------ | --------------- | ---------------------------------- |
| Conversation Agent | GPT-5.1         | Highest quality for roleplay       |
| Profiler Agent     | GPT-5.1         | Classification task                |
| Intel Collector    | Regex only      | No LLM needed; pattern matching    |
| Persona Engine     | GPT-5.1 + Faker | One-time generation per session    |

### Fallback Strategy (FR-039)

```text
Primary (GPT-5.1) unavailable
    -> Switch to GPT-4o-mini
    -> Notify user: "Using faster model"
    -> Continue functionality (quality may vary)
    -> Return to primary when available
```

## Database Schema (Supabase)

### `sessions`
- `id` (uuid, PK)
- `user_id` (uuid, FK auth.users)
- `title` (text)
- `attack_type` (text)
- `persona` (jsonb)
- `status` (text: 'active', 'archived')
- `created_at` (timestamptz)

### `messages`
- `id` (uuid, PK)
- `session_id` (uuid, FK sessions)
- `role` (text: 'user', 'assistant', 'scammer')
- `content` (text)
- `metadata` (jsonb)
- `created_at` (timestamptz)

### `ioc_extracted`
- `id` (uuid, PK)
- `session_id` (uuid, FK sessions)
- `type` (text: 'iban', 'btc', 'url', 'phone')
- `value` (text)
- `confidence` (float)
- `created_at` (timestamptz)

## API Endpoints (FastAPI)

| Endpoint                     | Method | Description                        |
| ---------------------------- | ------ | ---------------------------------- |
| `/api/auth/*`                | -      | Handled by Supabase Auth           |
| `/api/sessions`              | GET    | List user sessions                 |
| `/api/sessions`              | POST   | Create new session                 |
| `/api/sessions/{id}`         | GET    | Get session details                |
| `/api/sessions/{id}`         | DELETE | Delete session                     |
| `/api/sessions/{id}/chat`    | POST   | Stream chat response (SSE)         |
| `/api/sessions/{id}/export`  | GET    | Export JSON/CSV                    |

## LangGraph Workflow

```text
┌─────────────┐
│ START       │
└─────┬───────┘
      ▼
┌─────────────┐
│ Profiler    │ ──► Classify attack type
└─────┬───────┘
      ▼
┌─────────────┐
│ Persona     │ ──► Select/generate persona
└─────┬───────┘
      ▼
┌─────────────┐
│ Planner     │ ◄─────────────────────┐
└─────┬───────┘                       │
      ▼                               │
┌─────────────┐                       │
│ Generator   │ ──► Generate response │
└─────┬───────┘                       │
      ▼                               │
┌─────────────┐    unsafe             │
│ Safety      │ ──────────────────────┘
└─────┬───────┘
      │ safe
      ▼
┌─────────────┐
│ Human       │ ──► User approval (interrupt)
│ Approval    │
└─────┬───────┘
      │ approved
      ▼
┌─────────────┐
│ Intel       │ ──► Extract IOCs
│ Collector   │
└─────┬───────┘
      ▼
┌─────────────┐
│ END         │
└─────────────┘
```

## Dependencies

### Backend (Python)
```text
langgraph>=0.3.0
langchain-openai>=0.2.0
fastapi>=0.128.0
uvicorn>=0.40.0
pydantic>=2.12.0
supabase>=2.10.0
faker>=39.0.0
```

### Frontend (Node.js)
```text
next@16
react@19
ai (Vercel AI SDK)
@supabase/supabase-js
tailwindcss
shadcn/ui
```
