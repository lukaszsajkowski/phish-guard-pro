-- Migration: Create llm_usage table
-- Purpose: Record token usage and latency per LLM call
-- Affected tables: llm_usage (new)

create table public.llm_usage (
    id uuid primary key default gen_random_uuid(),
    session_id uuid references public.sessions(id) on delete cascade,
    agent text not null check (agent in ('profiler', 'conversation', 'eval')),
    model text not null,
    prompt_tokens int not null,
    completion_tokens int not null,
    latency_ms int not null,
    created_at timestamptz not null default now()
);

create index idx_llm_usage_session_id on public.llm_usage(session_id);
create index idx_llm_usage_agent on public.llm_usage(agent);

alter table public.llm_usage enable row level security;

create policy "Users can view LLM usage from their sessions"
    on public.llm_usage
    for select
    to authenticated
    using (
        exists (
            select 1 from public.sessions
            where sessions.id = llm_usage.session_id
            and sessions.user_id = auth.uid()
        )
    );

create policy "Users can create LLM usage in their sessions"
    on public.llm_usage
    for insert
    to authenticated
    with check (
        exists (
            select 1 from public.sessions
            where sessions.id = llm_usage.session_id
            and sessions.user_id = auth.uid()
        )
    );
