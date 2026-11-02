# Profiler eval fixtures (US-053)

`profiler_emails.jsonl` holds labelled emails for the offline comparison of Basal
against GPT-4o on attack-type classification. All content is synthetic: names are
Faker-style, IBANs and BTC addresses use public documentation examples, and domains
are `example.*`.

## Row schema (one JSON object per line)

| field       | meaning |
|-------------|---------|
| `id`        | unique, e.g. `pl-rom-01` (`<lang>-<label>-<nn>`) |
| `lang`      | `pl` or `en` |
| `gold`      | one of the nine `AttackType` values |
| `reviewed`  | `true` once the gold label passed blind review |
| `ambiguous` | `true` if blind review could not agree on one label; excluded from the gate |
| `email`     | the email text |
| `notes`     | author notes; rows starting with `HARD:` are deliberately hard cases and state the deciding cue |
| `review`    | `null` until reviewed, then `{"label_b", "label_c", "reviewer_model"}` |

## Label review procedure

Labels are written by the fixture author and must not be trusted until reviewed.

1. Review is **blind**. It is done by fresh Claude reviewers who see only `id` + `email`
   plus the nine options with their `ATTACK_TYPE_CRITERIA` descriptions
   (`phishguard.agents.prompts.profiler_basal`). Reviewers never see `gold`, `notes`,
   or any model output (Basal or GPT-4o). Do not look at model answers while reviewing.
2. Reviewer A labels every row. Rows where A matches `gold` get `reviewed: true`.
3. Mismatches go to a second fresh reviewer under the same blind rules.
4. If 2 of the 3 labels (gold, A, B) agree, that label becomes `gold` and the row gets
   `reviewed: true`. Otherwise the row gets `ambiguous: true`.
5. `review` is written on every row with `label_b`, `label_c` and `reviewer_model`.
6. `ambiguous` rows are excluded from the gate, and must be at most 10% of the set.
   If more, rewrite those emails and review them again.

## Review result (2026-11-02)

99/99 agreement from one blind reviewer, so no second reviewer was needed and no row is
`ambiguous`. Because the generator and the reviewer are both Claude models and agreement
was perfect, the set may be easier than real traffic. Treat fixture accuracy as an upper
bound and rely on Supabase/shadow data for realism.
