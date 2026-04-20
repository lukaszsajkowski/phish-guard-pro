-- Migration: Add 'ip' to ioc_extracted type check constraint
-- Purpose: Support IP address IOCs extracted by Intel Collector (US-036)
-- Affected tables: ioc_extracted

-- Drop the existing constraint and recreate it with 'ip' included
alter table public.ioc_extracted
    drop constraint ioc_extracted_type_check;

alter table public.ioc_extracted
    add constraint ioc_extracted_type_check
    check (type in ('iban', 'btc', 'url', 'phone', 'ip'));
