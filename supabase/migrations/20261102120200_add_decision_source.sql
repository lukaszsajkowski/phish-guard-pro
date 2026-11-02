-- Migration: Add decision_source to sessions
-- Purpose: Record which path (LLM or Basal) produced the attack classification
-- Affected tables: sessions (alter)

alter table public.sessions
    add column decision_source text
    check (decision_source in ('llm', 'basal', 'basal_low_confidence'));
