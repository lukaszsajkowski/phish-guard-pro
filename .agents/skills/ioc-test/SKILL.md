---
name: ioc-test
description: Test the Intel Collector IOC regex patterns against arbitrary text without hitting the LLM (e.g. `/ioc-test bc1qxy... and IBAN DE89...`, or `/ioc-test @path/to/sample.txt`). Use when the user wants to debug IOC extraction, verify a new regex, check a false positive/negative, or reproduce what Intel Collector would extract from a scammer message.
---

# /ioc-test — Run Intel Collector regexes against text

**Arguments:** `$ARGUMENTS` — the input text to scan. Two forms:
- **Inline** — the text itself: `/ioc-test contact me at +48 600 123 456 or bc1qxy...`
- **File reference** — starts with `@`: `/ioc-test @backend/tests/fixtures/scammer_msg_03.txt`

If `$ARGUMENTS` is empty, ask the user for text. If the inline text is ambiguous (e.g. starts with a path that isn't prefixed), ask.

## Your job

Run the live IOC extraction code (`backend/src/phishguard/agents/intel_collector.py`) against the input and produce a clear report of what was extracted, what was missed (if the user stated expectations), and any confidence scores. **No LLM calls.** This is a deterministic regex test.

## Why this skill exists

The project's Intel Collector is regex-only by design (no LLM in the extraction path — see PRD). Debugging it by running the full LangGraph workflow is wasteful. This skill lets you exercise just the extractor.

## Steps

1. **Resolve input**:
   - If `$ARGUMENTS` starts with `@`, Read the referenced file and use its contents as input text.
   - Otherwise use `$ARGUMENTS` verbatim as input text.
   - Preserve whitespace and unicode — scammer messages often rely on exotic spacing and homoglyphs.

2. **Locate the extractor**. The canonical implementation is `backend/src/phishguard/agents/intel_collector.py`. Confirm the class name and its public extraction method (Read the file if you're unsure — do not guess the API).

3. **Run the extractor** via a one-shot Python invocation:
   ```
   cd backend && uv run python -c "
   from phishguard.agents.intel_collector import IntelCollector
   import json
   text = '''<INPUT TEXT GOES HERE, triple-quoted, escape ''' if present>'''
   collector = IntelCollector()
   iocs = collector.extract(text)  # adjust to the real method name
   print(json.dumps([ioc.model_dump() for ioc in iocs], indent=2, default=str))
   "
   ```

   **Important:** Read `intel_collector.py` first to get the correct class + method signature before running. If the constructor requires dependencies (logger, config, db client), instantiate minimal stubs or use dependency defaults — do not invent parameters.

   If inline Python becomes fragile due to escaping (inputs with backticks, triple-quotes, nulls), fall back to writing the input to a temp file in `/tmp/ioc_test_input.txt` and reading from Python instead. Clean up the temp file at the end.

4. **Parse the output** and produce a report:

   ```
   IOC extraction report
   Input: 847 chars, 1 paragraph

   Found (4):
     BTC_WALLET   bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh   conf=0.95
     IBAN         DE89370400440532013000                       conf=1.00
     PHONE        +48 600 123 456                              conf=0.90
     URL          https://totally-legit-bank.example/verify    conf=0.85

   Not detected:
     (nothing flagged)
   ```

5. **If the user provided expectations** (e.g. "should also catch the XMR address"), diff expected vs actual and highlight misses and false positives. Otherwise just report what was found.

6. **Never mutate** `intel_collector.py`, its regexes, or any fixtures from this skill. If the user wants a pattern changed, delegate to `python-backend-dev` after confirming the fix plan.

## Hard rules

- No LLM calls. This skill exists specifically to bypass them.
- Never send the input text to any external service.
- Treat inputs as hostile — do not `eval` them, do not shell-interpolate them. Use Python string literals (triple-quoted) or file-based input.
- Do not commit or persist the input text anywhere. Scratch files in `/tmp/` only, cleaned up at the end.

## Communication

- Polish if the user writes in Polish.
- Lead with the found IOCs table. Short preamble only if something unusual happened (e.g. file not found, extractor signature changed).
