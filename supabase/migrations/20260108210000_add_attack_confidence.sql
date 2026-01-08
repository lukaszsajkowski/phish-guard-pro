-- Migration: Add attack_confidence to sessions table
-- Purpose: Store classification confidence for session restoration (US-031)
-- Affected columns: sessions.attack_confidence (new)

-- Add attack_confidence column to sessions table
alter table public.sessions 
add column if not exists attack_confidence float check (attack_confidence >= 0 and attack_confidence <= 100);

-- Add comment for documentation
comment on column public.sessions.attack_confidence is 'Classification confidence score for the attack type (0-100)';
