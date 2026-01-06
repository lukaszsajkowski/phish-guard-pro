-- Migration: Add turn_limit column to sessions table
--
-- Purpose: Implement session limits for US-015 (Session Limit Reached)
-- Affected tables: sessions
-- Special considerations: Default value of 20 per PRD FR-025

-- Add turn_limit column to sessions table
-- Default soft limit is 20 turns per session
alter table sessions
add column if not exists turn_limit integer not null default 20;

-- Add constraint to ensure turn_limit is positive
alter table sessions
add constraint sessions_turn_limit_positive check (turn_limit >= 1);

-- Add comment for documentation
comment on column sessions.turn_limit is 'Soft limit on conversation turns (default 20, extendable per US-015)';
