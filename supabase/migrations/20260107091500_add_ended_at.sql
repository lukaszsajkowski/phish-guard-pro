-- Migration: Add ended_at column to sessions table
-- Purpose: Track when sessions are ended/archived (US-017, US-018)
-- Affected tables: sessions

-- Add ended_at column to track when session was ended
alter table public.sessions add column ended_at timestamptz;

-- Create index for filtering ended sessions by time
create index idx_sessions_ended_at on public.sessions(ended_at);
