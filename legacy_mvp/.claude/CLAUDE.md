# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

PhishGuard is an autonomous agent-based system for Active Defense against phishing. Instead of passively blocking phishing emails, it engages attackers in believable conversation to waste their time (tarpitting) and extract threat intelligence (IOCs like crypto wallets, IBANs, phone numbers, URLs).

**MVP Mode**: Manual Simulation (Sandbox) - user pastes suspicious email content, and specialized AI agents collaborate to classify the attack, generate a victim persona, conduct engaging conversation, and extract IOCs in real-time.

## Tech Stack

- **Python 3.12+** with Pydantic for data validation
- **Streamlit** for UI (Chat Interface + Intel Dashboard sidebar)
- **OpenAI GPT-5.1** as primary LLM (GPT-4o-mini as fallback)
- **Faker** for generating consistent fake persona data (seeded per-session)
- **Regex validators + keyword blocklist** for safety layer

## Architecture

Four specialized agents with linear orchestration (no graph framework needed):

1. **Profiler Agent** - Classifies email into 8 categories: Nigerian 419, CEO Fraud, Fake Invoice, Romance Scam, Tech Support, Lottery/Prize, Crypto Investment, Delivery Scam
2. **Persona Engine** - Selects/generates victim persona (Naive Retiree, Stressed Manager, Greedy Investor, Confused Student) with consistent Faker-generated identity
3. **Conversation Agent** - Generates believable responses using "loose goals" strategy (obtain payment details, extend conversation, build trust, ask open-ended questions)
4. **Intel Collector** - Extracts IOCs from scammer messages using regex patterns (runs in parallel, no LLM)

**Safety Layer** (bidirectional):
- Input sanitization: prevents prompt injection, strips malicious formatting
- Output validation: blocks real PII formats (SSN, national ID), real corporate domains, sensitive financial data; auto-regenerates on unsafe content

## Key Functional Requirements

- Conversation soft limit: 20 exchanges (extendable)
- Response generation: <10 seconds
- Classification: <5 seconds
- IOC extraction: regex-based for BTC wallets (bc1/1/3 prefix), IBANs, phone numbers, URLs
- Export: JSON (full session) and CSV (IOCs only)
- End-of-game detection: detects when scammer unmasks the bot
- Graceful degradation: falls back to cheaper model on rate limits

## Development Commands

```bash
# Install dependencies (including dev)
uv sync --all-extras

# Run Streamlit app
uv run streamlit run src/phishguard/ui/app.py

# Run tests
uv run pytest

# Linting
uv run ruff check .

# Format code
uv run ruff format .
```

## Project Structure

```
src/phishguard/
├── agents/      # Profiler, Persona, Conversation agents
├── safety/      # Input sanitization, output validation
├── models/      # Pydantic schemas
└── ui/          # Streamlit app
tests/           # pytest tests
```
