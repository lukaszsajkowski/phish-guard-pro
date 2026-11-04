-- Migration: allow credential_phishing as a session attack type
-- Affected tables: sessions (check constraint only)

alter table public.sessions drop constraint sessions_attack_type_check;

alter table public.sessions add constraint sessions_attack_type_check
    check (attack_type in (
        'nigerian_419',
        'ceo_fraud',
        'fake_invoice',
        'romance_scam',
        'tech_support',
        'lottery_prize',
        'crypto_investment',
        'delivery_scam',
        'credential_phishing',
        'not_phishing'
    ));
