-- Migration: Create ioc_enrichment table
-- Purpose: Cache and persist enrichment data fetched from external sources
--          (BTC blockchain APIs, VirusTotal, AbuseIPDB, etc.) for individual
--          IOCs. Foundation for US-033; concrete sources land in US-034+.
-- Affected tables: ioc_enrichment (new)

create table public.ioc_enrichment (
    id uuid primary key default gen_random_uuid(),
    -- Optional FK: the service layer also caches enrichment for IOCs that
    -- are not yet linked to a session (e.g. pre-session warmup). Those rows
    -- are server-internal and not visible via RLS.
    ioc_id uuid references public.ioc_extracted(id) on delete cascade,
    source text not null,
    ioc_type text not null,
    value_hash text not null,
    status text not null check (status in ('ok', 'unavailable', 'rate_limited', 'error')),
    payload jsonb not null default '{}'::jsonb,
    fetched_at timestamptz not null default now()
);

-- Cache key: one entry per (source, ioc_type, value_hash) tuple. Upsertable.
create unique index idx_ioc_enrichment_cache_key
    on public.ioc_enrichment(source, ioc_type, value_hash);

-- TTL sweeps / time-based queries
create index idx_ioc_enrichment_fetched_at on public.ioc_enrichment(fetched_at);

-- Partial index for linked-IOC lookups (US-038 will hit this path)
create index idx_ioc_enrichment_ioc_id on public.ioc_enrichment(ioc_id)
    where ioc_id is not null;

-- Enable Row Level Security
alter table public.ioc_enrichment enable row level security;

-- RLS Policy: Allow authenticated users to select enrichment rows for IOCs
-- from sessions they own.
-- Ownership chain: ioc_enrichment.ioc_id -> ioc_extracted.session_id -> sessions.user_id
-- Cache rows with ioc_id = NULL are server-internal and invisible via RLS.
create policy "Users can view enrichment for their sessions' IOCs"
    on public.ioc_enrichment
    for select
    to authenticated
    using (
        ioc_id is not null
        and exists (
            select 1
            from public.ioc_extracted
            join public.sessions on sessions.id = ioc_extracted.session_id
            where ioc_extracted.id = ioc_enrichment.ioc_id
            and sessions.user_id = auth.uid()
        )
    );

-- RLS Policy: Allow authenticated users to insert enrichment for their own IOCs
-- Rationale: Frontend-triggered enrichment (US-038) creates rows via authed user.
create policy "Users can create enrichment for their sessions' IOCs"
    on public.ioc_enrichment
    for insert
    to authenticated
    with check (
        ioc_id is not null
        and exists (
            select 1
            from public.ioc_extracted
            join public.sessions on sessions.id = ioc_extracted.session_id
            where ioc_extracted.id = ioc_enrichment.ioc_id
            and sessions.user_id = auth.uid()
        )
    );

-- RLS Policy: Allow authenticated users to update enrichment for their own IOCs
-- Rationale: Refreshing stale cache entries or correcting payload shape.
create policy "Users can update enrichment for their sessions' IOCs"
    on public.ioc_enrichment
    for update
    to authenticated
    using (
        ioc_id is not null
        and exists (
            select 1
            from public.ioc_extracted
            join public.sessions on sessions.id = ioc_extracted.session_id
            where ioc_extracted.id = ioc_enrichment.ioc_id
            and sessions.user_id = auth.uid()
        )
    )
    with check (
        ioc_id is not null
        and exists (
            select 1
            from public.ioc_extracted
            join public.sessions on sessions.id = ioc_extracted.session_id
            where ioc_extracted.id = ioc_enrichment.ioc_id
            and sessions.user_id = auth.uid()
        )
    );

-- RLS Policy: Allow authenticated users to delete enrichment for their own IOCs
-- Rationale: Users can purge false-positive or outdated enrichment data.
create policy "Users can delete enrichment for their sessions' IOCs"
    on public.ioc_enrichment
    for delete
    to authenticated
    using (
        ioc_id is not null
        and exists (
            select 1
            from public.ioc_extracted
            join public.sessions on sessions.id = ioc_extracted.session_id
            where ioc_extracted.id = ioc_enrichment.ioc_id
            and sessions.user_id = auth.uid()
        )
    );

-- Note: No policies for anon role - unauthenticated users cannot access
-- enrichment data. The backend service role bypasses RLS for the internal
-- cache read/write path.
