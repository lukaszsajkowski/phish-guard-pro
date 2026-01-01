-- Migration: Create sessions table
-- Purpose: Store phishing simulation sessions for users
-- Affected tables: sessions (new)

-- Create sessions table to store phishing simulation sessions
create table public.sessions (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null references auth.users(id) on delete cascade,
    title text,
    attack_type text check (attack_type in (
        'nigerian_419',
        'ceo_fraud',
        'fake_invoice',
        'romance_scam',
        'tech_support',
        'lottery_prize',
        'crypto_investment',
        'delivery_scam',
        'not_phishing'
    )),
    persona jsonb,
    status text not null default 'active' check (status in ('active', 'archived')),
    created_at timestamptz not null default now()
);

-- Create index for faster user session lookups
create index idx_sessions_user_id on public.sessions(user_id);

-- Create index for filtering by status
create index idx_sessions_status on public.sessions(status);

-- Enable Row Level Security
-- RLS is always enabled, even for public tables, for security best practices
alter table public.sessions enable row level security;

-- RLS Policy: Allow authenticated users to select their own sessions
-- Rationale: Users should only see their own phishing simulation sessions
create policy "Users can view their own sessions"
    on public.sessions
    for select
    to authenticated
    using (auth.uid() = user_id);

-- RLS Policy: Allow authenticated users to insert their own sessions
-- Rationale: Users can create new simulation sessions for themselves
create policy "Users can create their own sessions"
    on public.sessions
    for insert
    to authenticated
    with check (auth.uid() = user_id);

-- RLS Policy: Allow authenticated users to update their own sessions
-- Rationale: Users can update status, title, or other fields of their sessions
create policy "Users can update their own sessions"
    on public.sessions
    for update
    to authenticated
    using (auth.uid() = user_id)
    with check (auth.uid() = user_id);

-- RLS Policy: Allow authenticated users to delete their own sessions
-- Rationale: Users can delete their own simulation sessions
create policy "Users can delete their own sessions"
    on public.sessions
    for delete
    to authenticated
    using (auth.uid() = user_id);

-- Note: No policies for anon role - unauthenticated users cannot access sessions
