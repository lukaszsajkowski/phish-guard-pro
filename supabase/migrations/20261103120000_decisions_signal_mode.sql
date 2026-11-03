-- Migration: Extend decisions for signal nodes (Basal next to a reference)
-- Purpose: Link a decision to a chat message, record what the reference (LLM or regex) answered, allow regex/none sources
-- Affected tables: decisions (alter: message_id, reference_kind, reference_answer; source check replaced)

alter table public.decisions
    add column message_id uuid null references public.messages(id) on delete cascade,
    add column reference_kind text null check (reference_kind in ('llm', 'regex')),
    add column reference_answer text null;

alter table public.decisions drop constraint decisions_source_check;
alter table public.decisions
    add constraint decisions_source_check
    check (source in ('basal', 'llm', 'basal_low_confidence', 'regex', 'none'));

-- Profiler rows compare Basal with the LLM answer.
update public.decisions
    set reference_kind = 'llm', reference_answer = llm_answer
    where node = 'profiler.attack_type';

create index idx_decisions_message_id on public.decisions(message_id);
