"""Arena report: turns saved results into EVALS.md and a PNG chart.

No LLM and no network. The output depends only on the saved results, so rendering
the same results twice gives identical bytes.
"""

from pathlib import Path

from phishguard.arena.metrics import (
    METRIC_STATUSES,
    Aggregate,
    Summary,
    within_noise,
)
from phishguard.arena.records import ConversationRecord
from phishguard.arena.runner import DEFAULT_SCENARIOS_DIR, RunMeta
from phishguard.arena.scenario import load_scenarios

SYSTEM_LABELS = {"phishguard": "PhishGuard", "baseline": "Baseline (plain LLM)"}
SENDER_LABELS = {"scammer": "Scammer", "victim": "PhishGuard persona"}
INVALID_WARNING_THRESHOLD = 0.10

# (metric key, column title, kind) for the four headline columns.
HEADLINE_COLUMNS = (
    ("secrets_revealed_share", "Secrets extracted", "pct"),
    ("turns_to_first_secret", "Turns to first secret", "turns"),
    ("suspected_bot", "Bot detected", "pct"),
    ("victim_cost_usd", "Cost / conversation", "usd"),
)


# --- formatting ---------------------------------------------------------------


def _fmt(value: float | None, kind: str) -> str:
    if value is None:
        return "n/a"
    if kind == "pct":
        return f"{value * 100:.1f}%"
    if kind == "usd":
        return f"${value:.4f}"
    return f"{value:.1f}"


def _fmt_agg(agg: Aggregate | None, kind: str) -> str:
    """'mean (min–max)' for one aggregate."""
    if agg is None or agg.mean is None:
        return "n/a"
    return f"{_fmt(agg.mean, kind)} ({_fmt(agg.min, kind)}–{_fmt(agg.max, kind)})"


def _label(system: str) -> str:
    return SYSTEM_LABELS.get(system, system)


def _table(header: list[str], rows: list[list[str]]) -> list[str]:
    lines = ["| " + " | ".join(header) + " |"]
    lines.append("|" + "|".join("---" for _ in header) + "|")
    lines += ["| " + " | ".join(r) + " |" for r in rows]
    return lines


# --- excerpt --------------------------------------------------------------------


def _secret_types(scenarios_dir: Path) -> dict[str, dict[str, str]]:
    """scenario id -> secret id -> secret type; empty when scenarios are missing."""
    try:
        scenarios = load_scenarios(scenarios_dir)
    except (OSError, ValueError):
        return {}
    return {s.id: {x.id: x.type for x in s.secrets} for s in scenarios}


def _first_reveal(record: ConversationRecord, wanted: set[str] | None) -> int | None:
    """Index of the first turn whose scammer message revealed a (wanted) secret."""
    for turn in record.turns:
        if turn.scammer is None:
            continue
        if any(wanted is None or r in wanted for r in turn.detected_reveals):
            return turn.index
    return None


def select_excerpt(
    results_dir: Path,
    override: str | None,
    scenarios_dir: Path = DEFAULT_SCENARIOS_DIR,
) -> tuple[ConversationRecord, int] | None:
    """Pick the conversation to quote and the turn where the secret is revealed.

    Default: the PhishGuard conversation with the earliest IBAN reveal (ties go to
    the file name that sorts first), else the earliest reveal of any secret;
    None when no conversation qualifies. Only completed and blocked-by-safety
    conversations count, and unreadable files are skipped. `override` is a
    conversation file stem and raises if that conversation cannot be used.
    """
    conv_dir = results_dir / "conversations"
    types = _secret_types(scenarios_dir)

    def load(path: Path) -> ConversationRecord | None:
        try:
            return ConversationRecord.model_validate_json(
                path.read_text(encoding="utf-8")
            )
        except (OSError, ValueError):
            return None

    def iban_ids(record: ConversationRecord) -> set[str]:
        by_id = types.get(record.scenario_id, {})
        return {sid for sid, kind in by_id.items() if kind == "iban"}

    def reveal_turn(record: ConversationRecord) -> int | None:
        """First IBAN reveal, else first reveal of anything."""
        ids = iban_ids(record)
        index = _first_reveal(record, ids) if ids else None
        return index if index is not None else _first_reveal(record, None)

    if override is not None:
        path = conv_dir / f"{override}.json"
        if not path.exists():
            raise FileNotFoundError(f"No conversation file: {path}")
        record = load(path)
        if record is None:
            raise ValueError(f"Conversation {override} is unreadable")
        index = reveal_turn(record)
        if index is None:
            raise ValueError(
                f"Conversation {override} has no revealed secret in a scammer message"
            )
        return record, index

    best_iban: tuple[int, str, ConversationRecord] | None = None
    best_any: tuple[int, str, ConversationRecord] | None = None
    for path in sorted(conv_dir.glob("*.json")):
        record = load(path)
        if (
            record is None
            or record.system != "phishguard"
            or record.status not in METRIC_STATUSES
        ):
            continue
        any_index = _first_reveal(record, None)
        if any_index is not None and (best_any is None or any_index < best_any[0]):
            best_any = (any_index, path.stem, record)
        ids = iban_ids(record)
        iban_index = _first_reveal(record, ids) if ids else None
        if iban_index is not None and (best_iban is None or iban_index < best_iban[0]):
            best_iban = (iban_index, path.stem, record)
    chosen = best_iban or best_any
    return None if chosen is None else (chosen[2], chosen[0])


SECRET_NOUNS = {
    "iban": "an IBAN",
    "btc": "a BTC address",
    "url": "a URL",
    "phone": "a phone number",
}


def _excerpt_section(
    excerpt: tuple[ConversationRecord, int] | None,
    results_rel: str,
    override: str | None,
    scenarios_dir: Path,
) -> list[str]:
    if excerpt is None:
        return [
            "## Example conversation",
            "",
            "No PhishGuard conversation with a revealed secret in this run.",
        ]
    record, reveal_turn = excerpt
    by_id = _secret_types(scenarios_dir).get(record.scenario_id, {})
    turn = next(t for t in record.turns if t.index == reveal_turn)
    kinds = sorted({by_id[r] for r in turn.detected_reveals if r in by_id})
    kind = "iban" if "iban" in kinds else (kinds[0] if kinds else None)
    noun = SECRET_NOUNS.get(kind or "", "a secret")
    is_pg = record.system == "phishguard"
    victim_label = SENDER_LABELS["victim"] if is_pg else _label(record.system)
    who = "the persona" if is_pg else "the baseline victim"
    messages: list[tuple[str, int, str]] = []
    for t in record.turns:
        if t.scammer is not None:
            messages.append(("scammer", t.index, t.scammer.message))
        if t.victim is not None:
            messages.append(("victim", t.index, t.victim.content))
    at = next(
        i
        for i, (sender, idx, _) in enumerate(messages)
        if sender == "scammer" and idx == reveal_turn
    )
    stem = f"{record.scenario_id}__{record.system}__r{record.repetition}"
    if override is not None:
        how = f"This conversation was chosen by hand (`--excerpt {override}`)."
    elif kind == "iban":
        how = (
            f"This is the {_label(record.system)} conversation with the earliest "
            "IBAN reveal, picked to show the mechanism, not a typical one."
        )
    else:
        how = (
            f"No {_label(record.system)} conversation revealed an IBAN, so this is "
            "the one with the earliest reveal of any secret, picked to show the "
            "mechanism, not a typical one."
        )
    lines = [
        f"## Example: {who} gets {noun}",
        "",
        f"Scenario `{record.scenario_id}`, repetition {record.repetition}, "
        f"revealed in turn {reveal_turn}. Messages are quoted unedited from the "
        f"saved conversation. {how}",
        "",
    ]
    for i in range(max(0, at - 2), min(len(messages), at + 2)):
        sender, idx, text = messages[i]
        marker = " (secret revealed here)" if i == at else ""
        name = SENDER_LABELS["scammer"] if sender == "scammer" else victim_label
        lines.append(f"**{name}**, turn {idx}{marker}:")
        lines.append("")
        lines += [f"> {part}" if part else ">" for part in text.splitlines() or [""]]
        lines.append("")
    lines.append(
        f"Full conversation: [{stem}.json]({results_rel}/conversations/{stem}.json)"
    )
    return lines


# --- markdown -------------------------------------------------------------------


def _headline_lines(summary: Summary) -> list[str]:
    systems = [s for s in ("phishguard", "baseline") if s in summary.headline]
    rows = [
        [_label(s)]
        + [
            _fmt_agg(summary.headline[s].get(key), kind)
            for key, _, kind in HEADLINE_COLUMNS
        ]
        for s in systems
    ]
    if "phishguard" in summary.headline and "baseline" in summary.headline:
        noise = []
        for key, _, _ in HEADLINE_COLUMNS:
            a = summary.headline["phishguard"][key]
            b = summary.headline["baseline"][key]
            noise.append(
                "within noise" if within_noise(a, b) else "ranges do not overlap"
            )
        rows.append(["Difference"] + noise)
    return _table(["System"] + [t for _, t, _ in HEADLINE_COLUMNS], rows)


def _scenario_set(summary: Summary, system: str) -> set[str]:
    return {
        r.scenario_id
        for r in summary.per_scenario
        if r.systems.get(system) is not None and r.systems[system].n > 0
    }


def _per_scenario_lines(summary: Summary, systems: list[str]) -> list[str]:
    header = ["Scenario", "Language", "Attack type", "Difficulty"]
    for s in systems:
        header += [f"{_label(s)}: secrets", "turns", "bot", "n"]
    rows = []
    for r in summary.per_scenario:
        row = [f"`{r.scenario_id}`", r.language, r.attack_type, r.difficulty]
        for s in systems:
            x = r.systems.get(s)
            if x is None or x.n == 0:
                row += ["n/a", "n/a", "n/a", "0"]
            else:
                row += [
                    _fmt(x.secrets_revealed_share, "pct"),
                    _fmt(x.turns_to_first_secret, "turns"),
                    _fmt(x.suspected_bot, "pct"),
                    str(x.n),
                ]
        rows.append(row)
    return _table(header, rows)


def render_markdown(
    summary: Summary,
    meta: RunMeta,
    excerpt: tuple[ConversationRecord, int] | None,
    chart_path: str,
    results_rel: str,
    excerpt_override: str | None = None,
    scenarios_dir: Path = DEFAULT_SCENARIOS_DIR,
) -> str:
    """Render EVALS.md. Links are relative to the repository root."""
    systems = [s for s in ("phishguard", "baseline") if s in summary.headline]
    n_scen = len(meta.scenario_ids)
    out: list[str] = ["# Scammer Arena results", ""]

    if summary.invalid_share > INVALID_WARNING_THRESHOLD:
        out += [
            f"> **Warning:** {summary.invalid_share * 100:.1f}% of the conversations "
            "were invalid (for example model refusals) and are excluded from the "
            "numbers below. Treat the comparison with extra care.",
            "",
        ]

    out += [
        "Experimental results from Scammer Arena, a proof-of-concept harness that "
        "plays a scripted scammer (an LLM) against PhishGuard and against a plain "
        "LLM baseline on the same fictional scenarios. "
        f"Run date {meta.date}, commit `{meta.commit}`, model `{meta.model}`.",
        "",
        "## PhishGuard vs plain LLM without the graph",
        "",
        f"Each cell is the mean of {meta.repetitions} repetitions, "
        f"each repetition averaged over {n_scen} scenarios, with the min–max range "
        "in brackets.",
        "",
        *_headline_lines(summary),
        "",
        f"![PhishGuard vs baseline]({chart_path})",
        "",
        *_excerpt_section(excerpt, results_rel, excerpt_override, scenarios_dir),
        "",
        "## Caveats",
        "",
        "- This simulation is not production. The scammer is an LLM following a "
        "script, and real scammers behave differently.",
        f"- The same model (`{meta.model}`) plays both sides, which may inflate the "
        "results.",
        f"- The sample is small: {n_scen} scenarios × {meta.repetitions} repetitions "
        "per system. The min–max ranges show run-to-run spread but are not a "
        "statistical test.",
        "- All data is fictional: emails, personas, IBANs, wallets, phone numbers "
        "and URLs are made up, though formally valid.",
        "- Comparison with published results (Siadati et al., Puppeteer) is only "
        "indicative, because the setups differ.",
        "",
        "## Method",
        "",
        "- A conversation is one scenario, one system and one repetition, with at "
        "most 10 turns. Turn 0 is the victim's first reply to the phishing email; "
        "later turns are a scammer message followed by a victim reply.",
        "- The scenario setup (email classification and persona) runs once per "
        "scenario and is shared by both systems and all repetitions.",
        "- PhishGuard runs the application's own graphs, prompts, IOC extraction "
        "and safety layer in Python, with human approval replaced by an automatic "
        "pass. The baseline uses the same model and persona with one plain LLM call "
        "per turn, a simple victim prompt that also asks it to keep the scammer "
        "talking and get payment details, and no graph, IOC extraction or safety "
        "layer.",
        "- A secret counts as revealed when its value appears in a scammer message "
        "(after lowercasing both and removing whitespace, hyphens and "
        "parentheses, and ignoring trailing punctuation), not when the scammer "
        "claims it.",
        "- Secrets extracted: revealed secrets divided by all secrets in the "
        "scenario. Turns to first secret: the turn of the first reveal; "
        "conversations with no reveal are left out of this mean. Bot detected: "
        "share of conversations in which the scammer suspected a bot at least "
        "once. Cost: victim-side LLM cost per conversation; for PhishGuard it "
        "includes the scenario setup cost split evenly across its conversations. "
        "Scammer cost is not included.",
        "- Conversations marked invalid (for example repeated model refusals) or "
        "failed with an error are excluded from the metrics.",
        f"- Run date {meta.date}, commit `{meta.commit}`, model `{meta.model}`.",
        "",
        "## Detailed results",
        "",
        "### Conversations",
        "",
    ]

    count_rows = []
    for s in systems:
        c = summary.counts[s]
        count_rows.append(
            [_label(s)]
            + [
                str(v)
                for v in (
                    c.expected,
                    c.completed,
                    c.blocked_by_safety,
                    c.invalid,
                    c.error,
                    c.missing,
                )
            ]
        )
    out += _table(
        [
            "System",
            "Expected",
            "Completed",
            "Blocked by safety",
            "Invalid",
            "Error",
            "Missing",
        ],
        count_rows,
    )
    missing = {s: summary.counts[s].missing for s in systems}
    unreadable = summary.unreadable_files
    out += [
        "",
        "Missing conversation files: "
        + ", ".join(f"{_label(s)} {missing[s]}" for s in systems)
        + f" ({sum(missing.values())} in total).",
        "",
        "Conversations with no secret revealed (excluded from turns to first "
        "secret): "
        + ", ".join(
            f"{_label(s)} {summary.no_reveal_conversations.get(s, 0)}" for s in systems
        )
        + ".",
    ]
    out += [
        "",
        f"Unreadable conversation files (corrupt or truncated, skipped): "
        f"{len(unreadable)}"
        + (": " + ", ".join(f"`{n}`" for n in unreadable) if unreadable else "")
        + ".",
    ]
    sets = {s: _scenario_set(summary, s) for s in systems}
    if len({frozenset(v) for v in sets.values()}) > 1:
        out += [
            "",
            "The systems were averaged over different scenario sets because some "
            "conversations are invalid, failed or missing: "
            + ", ".join(
                f"{_label(s)} {len(sets[s])} of {n_scen} scenarios" for s in systems
            )
            + ". The headline comparison is therefore not like for like.",
        ]

    out += ["", "### Per scenario", "", *_per_scenario_lines(summary, systems), ""]

    out += ["### English and Polish scenarios", ""]
    lang_rows = []
    for lang in sorted(summary.by_language):
        for s in systems:
            block = summary.by_language[lang].get(s, {})
            lang_rows.append(
                [lang, _label(s)]
                + [_fmt_agg(block.get(key), kind) for key, _, kind in HEADLINE_COLUMNS]
            )
    out += _table(
        ["Language", "System"] + [t for _, t, _ in HEADLINE_COLUMNS], lang_rows
    )

    out += ["", "### Other measures", ""]
    other = (
        ("engagement_turns", "Engagement (turns)", "turns"),
        ("unmasking_detected", "Unmasking flagged", "pct"),
        ("victim_latency_ms", "Victim latency per conversation (ms)", "turns"),
    )
    out += _table(
        ["System"] + [t for _, t, _ in other],
        [
            [_label(s)]
            + [_fmt_agg(summary.headline[s].get(key), kind) for key, _, kind in other]
            for s in systems
        ],
    )

    ioc, safety, split = summary.ioc, summary.safety, summary.cost_split
    out += [
        "",
        "### PhishGuard IOC extraction",
        "",
        f"- Recall: {_fmt(ioc.recall, 'pct')} ({ioc.true_positives} of "
        f"{ioc.revealed} revealed secrets found in the extracted IOCs).",
        f"- Precision: {_fmt(ioc.precision, 'pct')} "
        f"({ioc.extracted - ioc.false_positives} of {ioc.extracted} extracted IOCs "
        "match a secret or a known IOC of the scenario).",
        "",
        "### PhishGuard safety",
        "",
        f"- Conversations counted: {safety.conversations}; "
        f"blocked by safety: {safety.blocked_conversations}.",
        f"- Draft replies regenerated: {safety.regenerations} across "
        f"{safety.turns_with_regeneration} turns.",
        f"- Replies sent while still unsafe: {safety.unsafe_replies_sent} "
        "(expected 0).",
        "",
        "### PhishGuard cost split",
        "",
        *_table(
            ["Part", "Cost / conversation"],
            [
                ["Setup (classification and persona)", _fmt_agg(split.setup, "usd")],
                ["Turns", _fmt_agg(split.turns, "usd")],
                ["Total", _fmt_agg(split.total, "usd")],
            ],
        ),
        "",
        "### Profiler agreement",
        "",
    ]
    pa = summary.profiler_agreement
    if pa.n == 0:
        out.append("No classification results available.")
    else:
        out.append(
            f"The profiler matched the scenario's attack type in {pa.agreed} of "
            f"{pa.n} scenarios ({_fmt(pa.share, 'pct')}). A classification of "
            "`not_phishing` counts as a disagreement."
        )
        if pa.mismatches:
            out += [""]
            out += _table(
                ["Scenario", "Expected", "Profiler said"],
                [
                    [f"`{m.scenario_id}`", m.expected, m.got or "n/a"]
                    for m in pa.mismatches
                ],
            )

    out += [
        "",
        "## How to reproduce",
        "",
        "Run these from `backend/`. The first command needs an `OPENAI_API_KEY` in "
        "the environment and makes paid API calls; the second only reads the saved "
        "results.",
        "",
        "```bash",
        "uv run python -m phishguard.arena run",
        "uv run python -m phishguard.arena report",
        "```",
        "",
        f"Saved conversations for this report are in `{results_rel}/`.",
        "",
    ]
    return "\n".join(out)


# --- chart ----------------------------------------------------------------------


def render_chart(summary: Summary, path: Path) -> None:
    """Grouped bars, PhishGuard vs baseline, one panel per headline metric."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    grey = "#8b949e"
    colors = {"phishguard": "#2f81f7", "baseline": "#d29922"}
    systems = [s for s in ("phishguard", "baseline") if s in summary.headline]
    scale = {"pct": 100.0, "turns": 1.0, "usd": 1.0}

    with plt.rc_context(
        {
            "text.color": grey,
            "axes.labelcolor": grey,
            "axes.edgecolor": grey,
            "xtick.color": grey,
            "ytick.color": grey,
            "font.family": "DejaVu Sans",
        }
    ):
        fig, axes = plt.subplots(1, len(HEADLINE_COLUMNS), figsize=(11, 3.8), dpi=150)
        for ax, (key, title, kind) in zip(axes, HEADLINE_COLUMNS, strict=True):
            for i, s in enumerate(systems):
                agg = summary.headline[s][key]
                if agg.mean is None:
                    ax.text(i, 0, "n/a", ha="center", va="bottom", color=grey)
                    continue
                k = scale[kind]
                mean, lo, hi = agg.mean * k, agg.min * k, agg.max * k
                ax.bar(i, mean, width=0.6, color=colors[s])
                ax.errorbar(
                    i,
                    mean,
                    yerr=[[mean - lo], [hi - mean]],
                    color=grey,
                    capsize=4,
                    linewidth=1.2,
                )
                ax.annotate(
                    _fmt(agg.mean, kind),
                    (i, hi),
                    xytext=(0, 4),
                    textcoords="offset points",
                    ha="center",
                    fontsize=8,
                    color=grey,
                )
            ax.set_title(title, fontsize=10, color=grey)
            ax.set_xticks(range(len(systems)))
            ax.set_xticklabels(
                ["PhishGuard" if s == "phishguard" else "Baseline" for s in systems],
                fontsize=9,
            )
            ax.set_xlim(-0.6, len(systems) - 0.4)
            ax.set_ylim(bottom=0)
            ax.margins(y=0.15)
            ax.set_facecolor("none")
            for side in ("top", "right"):
                ax.spines[side].set_visible(False)
            if kind == "pct":
                ax.set_ylabel(
                    "% of conversations" if key == "suspected_bot" else "% of secrets"
                )
            elif kind == "usd":
                ax.set_ylabel("USD")
            else:
                ax.set_ylabel("turns")
        fig.suptitle(
            f"PhishGuard vs plain LLM baseline (mean, bars show min–max), "
            f"{summary.meta.date}",
            fontsize=10,
            color=grey,
        )
        fig.tight_layout()
        path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(path, transparent=True, metadata={"Software": None})
        plt.close(fig)
