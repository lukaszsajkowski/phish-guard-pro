-- Migration: Create messages table
-- Purpose: Store conversation messages within phishing simulation sessions
-- Affected tables: messages (new)

-- Create messages table to store conversation history
create table public.messages (
    id uuid primary key default gen_random_uuid(),
    session_id uuid not null references public.sessions(id) on delete cascade,
    role text not null check (role in ('user', 'assistant', 'scammer')),
    content text not null,
    metadata jsonb,
    created_at timestamptz not null default now()
);

-- Create index for faster session message lookups
create index idx_messages_session_id on public.messages(session_id);

-- Create index for ordering messages by creation time
create index idx_messages_created_at on public.messages(created_at);

-- Enable Row Level Security
alter table public.messages enable row level security;

-- RLS Policy: Allow authenticated users to select messages from their own sessions
-- Rationale: Users should only see messages from sessions they own
create policy "Users can view messages from their sessions"
    on public.messages
    for select
    to authenticated
    using (
        exists (
            select 1 from public.sessions
            where sessions.id = messages.session_id
            and sessions.user_id = auth.uid()
        )
    );

-- RLS Policy: Allow authenticated users to insert messages to their own sessions
-- Rationale: Users can add messages to their own simulation sessions
create policy "Users can create messages in their sessions"
    on public.messages
    for insert
    to authenticated
    with check (
        exists (
            select 1 from public.sessions
            where sessions.id = messages.session_id
            and sessions.user_id = auth.uid()
        )
    );

-- RLS Policy: Allow authenticated users to update messages in their own sessions
-- Rationale: Users can edit messages (e.g., edit before send feature)
create policy "Users can update messages in their sessions"
    on public.messages
    for update
    to authenticated
    using (
        exists (
            select 1 from public.sessions
            where sessions.id = messages.session_id
            and sessions.user_id = auth.uid()
        )
    )
    with check (
        exists (
            select 1 from public.sessions
            where sessions.id = messages.session_id
            and sessions.user_id = auth.uid()
        )
    );

-- RLS Policy: Allow authenticated users to delete messages from their own sessions
-- Rationale: Users can delete messages from their sessions
create policy "Users can delete messages from their sessions"
    on public.messages
    for delete
    to authenticated
    using (
        exists (
            select 1 from public.sessions
            where sessions.id = messages.session_id
            and sessions.user_id = auth.uid()
        )
    );

-- Note: No policies for anon role - unauthenticated users cannot access messages
