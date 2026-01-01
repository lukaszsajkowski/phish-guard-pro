-- Migration: Create ioc_extracted table
-- Purpose: Store Indicators of Compromise extracted from scammer messages
-- Affected tables: ioc_extracted (new)

-- Create ioc_extracted table to store threat indicators
create table public.ioc_extracted (
    id uuid primary key default gen_random_uuid(),
    session_id uuid not null references public.sessions(id) on delete cascade,
    type text not null check (type in ('iban', 'btc', 'url', 'phone')),
    value text not null,
    confidence float not null check (confidence >= 0 and confidence <= 1),
    created_at timestamptz not null default now()
);

-- Create index for faster session IOC lookups
create index idx_ioc_extracted_session_id on public.ioc_extracted(session_id);

-- Create index for filtering by IOC type
create index idx_ioc_extracted_type on public.ioc_extracted(type);

-- Enable Row Level Security
alter table public.ioc_extracted enable row level security;

-- RLS Policy: Allow authenticated users to select IOCs from their own sessions
-- Rationale: Users should only see IOCs from sessions they own
create policy "Users can view IOCs from their sessions"
    on public.ioc_extracted
    for select
    to authenticated
    using (
        exists (
            select 1 from public.sessions
            where sessions.id = ioc_extracted.session_id
            and sessions.user_id = auth.uid()
        )
    );

-- RLS Policy: Allow authenticated users to insert IOCs to their own sessions
-- Rationale: System can add IOCs detected during conversation simulation
create policy "Users can create IOCs in their sessions"
    on public.ioc_extracted
    for insert
    to authenticated
    with check (
        exists (
            select 1 from public.sessions
            where sessions.id = ioc_extracted.session_id
            and sessions.user_id = auth.uid()
        )
    );

-- RLS Policy: Allow authenticated users to update IOCs in their own sessions
-- Rationale: Allows correction of confidence scores or values if needed
create policy "Users can update IOCs in their sessions"
    on public.ioc_extracted
    for update
    to authenticated
    using (
        exists (
            select 1 from public.sessions
            where sessions.id = ioc_extracted.session_id
            and sessions.user_id = auth.uid()
        )
    )
    with check (
        exists (
            select 1 from public.sessions
            where sessions.id = ioc_extracted.session_id
            and sessions.user_id = auth.uid()
        )
    );

-- RLS Policy: Allow authenticated users to delete IOCs from their own sessions
-- Rationale: Users can remove false positive IOCs
create policy "Users can delete IOCs from their sessions"
    on public.ioc_extracted
    for delete
    to authenticated
    using (
        exists (
            select 1 from public.sessions
            where sessions.id = ioc_extracted.session_id
            and sessions.user_id = auth.uid()
        )
    );

-- Note: No policies for anon role - unauthenticated users cannot access IOCs
