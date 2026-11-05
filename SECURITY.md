# Security Policy

## Reporting a vulnerability

Please report security issues privately through GitHub's **Report a vulnerability** button on the [Security tab](https://github.com/lukaszsajkowski/phish-guard-pro/security) of this repository. Do not open a public issue for a vulnerability.

Include what you found, how to reproduce it and what impact you expect. This is a personal project, so responses are best effort; I aim to acknowledge reports within a week.

## Scope

In scope: the code in this repository (FastAPI backend, Next.js frontend, Supabase migrations), including:

- prompt injection or other ways a scammer's message can make the agents act outside their role
- ways the safety layer can be bypassed so that a reply leaks real personal data
- authentication, authorization and Row Level Security issues
- secrets or credentials exposed by the code or the build

Out of scope: third-party services the project calls (OpenAI, Anthropic, VirusTotal, AbuseIPDB, NumVerify, mempool.space, Supabase) and vulnerabilities that need a compromised developer machine.

## Personal data

PhishGuard Pro never sends real personal data to scammers: personas are generated with Faker and outgoing replies are checked by the safety layer. Please do not include real personal data, real victims' emails or live credentials in your report; redact them or use fictional values.
