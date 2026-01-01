# PhishGuard

An autonomous agent-based system for **Active Defense** against phishing.
Instead of passively blocking phishing emails, PhishGuard engages attackers
in believable conversation to waste their time (tarpitting) and extract
threat intelligence (IOCs).

## Overview

PhishGuard operates in **Manual Simulation mode (Sandbox)**, where users
paste suspicious email content and four specialized AI agents collaborate to:

- **Classify** the type of phishing attack (8 categories)
- **Generate** an appropriate "victim" persona
- **Conduct** engaging but safe conversation
- **Extract** Indicators of Compromise (IOCs) in real-time

### Business Goals

| Goal         | Description                                      |
| ------------ | ------------------------------------------------ |
| Tarpitting   | Maximize time attackers waste with the bot       |
| Threat Intel | Extract key indicators (wallets, IBANs, domains) |
| Safety       | Demonstrate safe LLM usage with no data leakage  |

## Features

### Core Functionality

- **Attack Classification**: Automatically classifies emails into 8 categories:
  - Nigerian 419 Scam
  - CEO Fraud
  - Fake Invoice
  - Romance Scam
  - Tech Support Scam
  - Lottery/Prize Scam
  - Crypto Investment Scam
  - Delivery Scam

- **Persona Engine**: 4 victim personas with consistent Faker-generated identities:
  - Naive Retiree
  - Stressed Manager
  - Greedy Investor
  - Confused Student

- **Conversation Agent**: Generates believable responses using "loose goals" strategy:
  - Obtain payment details
  - Extend conversation
  - Build trust
  - Ask open-ended questions

- **Intel Collector**: Real-time IOC extraction via regex:
  - BTC wallet addresses (bc1/1/3 prefix)
  - IBAN numbers
  - Phone numbers (international formats)
  - Malicious URLs

### Safety Layer (Bidirectional)

- **Input Sanitization**: Prevents prompt injection, strips malicious formatting
- **Output Validation**: Blocks real PII (SSN, national IDs), corporate domains
- **Auto-regeneration**: Automatically regenerates unsafe responses
- **Unmasking Detection**: Detects when scammer identifies the bot

### Intel Dashboard

Real-time side panel displaying:

- Attack type with confidence score
- Collected IOCs with priority coloring
- Risk Score (1-10 scale)
- Extraction timeline

### Additional Features

- Edit responses before copying
- Copy to clipboard functionality
- Session soft limit (20 turns, extendable)
- Demo mode with pre-loaded scenarios
- Export to JSON (full session) and CSV (IOCs only)
- Graceful degradation with fallback model
- Agent thinking panel (collapsible)

## Tech Stack

| Component       | Technology        | Rationale                         |
| --------------- | ----------------- | --------------------------------- |
| Backend         | Python 3.12+      | Standard, well-supported          |
| UI              | Streamlit         | Chat interface + sidebar          |
| LLM Primary     | GPT-5.1           | Quality for conversation/roleplay |
| LLM Fallback    | GPT-4o-mini       | Cost optimization, degradation    |
| Data Validation | Pydantic v2       | Type safety and validation        |
| Fake Data       | Faker             | Seeded per-session consistency    |
| Safety          | Regex + Blocklist | Bidirectional validation          |

## Architecture

```text
Email → Profiler Agent → Persona Engine → [Conversation Loop] → Summary
                                                ↑
                          Scammer message → Intel Collector
```

Four specialized agents with linear orchestration:

1. **Profiler Agent** - Classifies email into 8 categories with confidence score
2. **Persona Engine** - Selects/generates victim persona with Faker identity
3. **Conversation Agent** - Generates believable responses in persona style
4. **Intel Collector** - Extracts IOCs using regex patterns (no LLM)

## Installation

### Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) package manager
- OpenAI API key

### Setup

```bash
# Clone the repository
git clone https://github.com/yourusername/phish-guard.git
cd phish-guard

# Install dependencies
uv sync --all-extras

# Create .env file with your OpenAI API key
cp .env.example .env
# Edit .env and add your OPENAI_API_KEY
```

### Environment Variables

Create a `.env` file in the project root:

```env
OPENAI_API_KEY=your-api-key-here
```

## Usage

### Running the Application

```bash
uv run streamlit run src/phishguard/ui/app.py
```

The application will open in your browser at `http://localhost:8501`.

### Workflow

1. **Paste Email**: Paste suspicious phishing email content
2. **Analyze**: Click "Analyze" to classify the attack
3. **Review**: Review classification and auto-selected persona
4. **Generate**: Generate victim responses
5. **Iterate**: Paste scammer replies to continue conversation
6. **Extract**: Monitor IOCs in the Intel Dashboard
7. **Export**: Export session data as JSON or IOCs as CSV

### Demo Mode

Click "Demo Mode" on the start screen to explore pre-loaded scenarios
without API calls:

- Nigerian 419 Scam
- CEO Fraud
- Crypto Investment Scam

## Project Structure

```text
src/phishguard/
├── agents/              # AI agent implementations
│   ├── profiler.py      # Email classification
│   ├── persona_engine.py # Persona selection/generation
│   ├── conversation.py  # Response generation
│   ├── intel_collector.py # IOC extraction (regex)
│   └── prompts/         # LLM prompt templates
├── models/              # Pydantic schemas
│   ├── session.py       # Session state management
│   ├── classification.py # Attack types and results
│   ├── persona.py       # Persona definitions
│   ├── ioc.py           # IOC models
│   ├── conversation.py  # Message models
│   └── demo.py          # Demo scenario models
├── safety/              # Safety layer
│   ├── input_sanitizer.py  # Input validation
│   ├── output_validator.py # Output validation
│   └── unmasking_detector.py # Bot detection
├── ui/                  # Streamlit interface
│   ├── app.py           # Main application
│   └── components/      # UI components
├── demo/                # Demo scenarios
│   └── scenarios.py     # Pre-loaded examples
├── llm/                 # LLM client
│   └── client.py        # OpenAI integration with retry
└── export.py            # JSON/CSV export
tests/                   # pytest test suite
```

## Development

### Commands

```bash
# Install all dependencies (including dev)
uv sync --all-extras

# Run the application
uv run streamlit run src/phishguard/ui/app.py

# Run tests
uv run pytest

# Run tests with coverage
uv run pytest --cov=src/phishguard

# Lint code
uv run ruff check .

# Format code
uv run ruff format .
```

### Code Quality

The project uses:

- **Ruff** for linting and formatting
- **pytest** for testing
- **Pydantic v2** for data validation
- **Type hints** throughout

## Performance Targets

| Metric              | Target                  |
| ------------------- | ----------------------- |
| Classification Time | < 5 seconds             |
| Response Generation | < 10 seconds            |
| IOC Extraction      | < 2 seconds             |
| Safety Score        | 100% (zero PII leakage) |

## Safety Features

### What Gets Blocked

- Real SSN/National ID patterns
- Real credit card numbers
- Real corporate domains (from blocklist)
- Real email addresses
- Sensitive financial data formats

### What Gets Allowed

- Faker-generated fake identities
- Fake addresses and phone numbers
- Fictional payment details
- Safe placeholder data

## Limitations (MVP)

| Not Included                  | Reason                        |
| ----------------------------- | ----------------------------- |
| Email automation (SMTP/IMAP)  | Spam risk, complexity         |
| Image generation              | Abuse risk                    |
| Persistent database           | MVP uses session_state        |
| Multilingual support          | English-only for MVP          |
| Mobile responsiveness         | Desktop-first (min 1024px)    |

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE)
file for details.

```text
MIT License

Copyright (c) 2025 PhishGuard Contributors

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## Acknowledgments

Built as a demonstration of AI architecture capabilities in the cybersecurity
domain.
