-- Migration: Create decisions table
-- Purpose: Log Basal/LLM routing decisions for closed questions (no email text stored)
-- Affected tables: decisions (new)

create table public.decisions (
    id uuid primary key default gen_random_uuid(),
    session_id uuid not null references public.sessions(id) on delete cascade,
    node text not null,
    mode text not null check (mode in ('shadow', 'live')),
    options jsonb not null,
    basal_answer text,
    basal_probabilities jsonb,
    basal_confidence float,
    basal_ms int,
    basal_model text,
    threshold float not null,
    skip_reason text check (skip_reason in ('disabled', 'language', 'unavailable', 'timeout', 'below_threshold')),
    llm_answer text,
    llm_model text,
    llm_ms int,
    final_answer text not null,
    source text not null check (source in ('basal', 'llm', 'basal_low_confidence')),
    created_at timestamptz not null default now()
);

create index idx_decisions_session_id on public.decisions(session_id);
create index idx_decisions_node on public.decisions(node);

alter table public.decisions enable row level security;

create policy "Users can view decisions from their sessions"
    on public.decisions
    for select
    to authenticated
    using (
        exists (
            select 1 from public.sessions
            where sessions.id = decisions.session_id
            and sessions.user_id = auth.uid()
        )
    );

create policy "Users can create decisions in their sessions"
    on public.decisions
    for insert
    to authenticated
    with check (
        exists (
            select 1 from public.sessions
            where sessions.id = decisions.session_id
            and sessions.user_id = auth.uid()
        )
    );
