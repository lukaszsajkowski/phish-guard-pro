"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { formatDistanceToNow } from "date-fns";
import {
    AlertCircle,
    Shield,
    Link,
    Search,
    Loader2,
    ChevronDown,
    ChevronUp,
    RefreshCw,
    BadgeCheck,
    Copy,
    Check,
} from "lucide-react";
import { ExtractedIOC, TimelineEvent, RiskScoreBreakdown as RiskScoreBreakdownType, EnrichmentState, ReputationLabel } from "@/types/schemas";
import {
    IOC_ICONS,
    IOC_LABELS,
    ATTACK_TYPE_LABELS,
    getRiskLabel,
} from "@/lib/constants/ioc";
import { RiskScoreBreakdown } from "./RiskScoreBreakdown";
import { useEnrichment, deriveThreatAssessment } from "@/hooks/useEnrichment";
import { defangUrl } from "@/lib/utils";

interface IntelDashboardProps {
    iocs: ExtractedIOC[];
    attackType?: string;
    confidence?: number;
    riskScore?: number;
    riskScoreBreakdown?: RiskScoreBreakdownType;
    timeline?: TimelineEvent[];
    isLoading?: boolean;
    /** When provided, enables the "Enrich" button on each IOC card. */
    getAccessToken?: () => Promise<string | null>;
    /**
     * When true, auto-enrich ALL IOC types on load (not just BTC).
     * Use in history view where cached enrichment data should be restored.
     */
    autoEnrichAll?: boolean;
    /**
     * US-040: Called after any IOC enrichment succeeds, so the parent can
     * re-fetch the risk score breakdown (which now incorporates reputation data).
     */
    onEnrichmentComplete?: () => void;
}

// ---------------------------------------------------------------------------
// Threat-score colour helpers (0-100 scale)
// ---------------------------------------------------------------------------

function getThreatScoreColor(score: number): string {
    if (score <= 33) return "text-green-500";
    if (score <= 66) return "text-yellow-500";
    return "text-red-500";
}

function getReputationBadge(reputation: ReputationLabel) {
    const map: Record<ReputationLabel, { label: string; className: string; dotClass: string }> = {
        malicious: {
            label: "MALICIOUS",
            className: "text-[color:var(--pg-red)]",
            dotClass: "bg-[color:var(--pg-red)] shadow-[0_0_4px_var(--pg-red)]",
        },
        suspicious: {
            label: "SUSPICIOUS",
            className: "text-[color:var(--pg-amber)]",
            dotClass: "bg-[color:var(--pg-amber)] shadow-[0_0_4px_var(--pg-amber)]",
        },
        clean: {
            label: "CLEAN",
            className: "text-green-500",
            dotClass: "bg-[color:var(--pg-green)] shadow-[0_0_4px_var(--pg-green)]",
        },
        unknown: {
            label: "UNKNOWN",
            className: "text-muted-foreground",
            dotClass: "bg-muted-foreground",
        },
    };
    return map[reputation] ?? map.unknown;
}

// ---------------------------------------------------------------------------
// IOC type icon background color helpers (for 26px colored square)
// ---------------------------------------------------------------------------

function getIocTypeIconColors(type: string): { bg: string; border: string; text: string } {
    const map: Record<string, { bg: string; border: string; text: string }> = {
        phone: {
            bg: "bg-[color:var(--pg-green-dim)]",
            border: "border-[color:var(--pg-green)]",
            text: "text-[color:var(--pg-green)]",
        },
        btc: {
            bg: "bg-[color:var(--pg-amber-dim)]",
            border: "border-[color:var(--pg-amber)]",
            text: "text-[color:var(--pg-amber)]",
        },
        btc_wallet: {
            bg: "bg-[color:var(--pg-amber-dim)]",
            border: "border-[color:var(--pg-amber)]",
            text: "text-[color:var(--pg-amber)]",
        },
        iban: {
            bg: "bg-[color:var(--pg-blue-dim)]",
            border: "border-[color:var(--pg-blue)]",
            text: "text-[color:var(--pg-blue)]",
        },
        url: {
            bg: "bg-[color:var(--pg-accent-dim)]",
            border: "border-[color:var(--pg-accent)]",
            text: "text-[color:var(--pg-accent)]",
        },
        ip: {
            bg: "bg-[color:var(--pg-accent-dim)]",
            border: "border-[color:var(--pg-accent)]",
            text: "text-[color:var(--pg-accent)]",
        },
    };
    return map[type] ?? map.url;
}

// ---------------------------------------------------------------------------
// Radial Gauge sub-component (US-044)
// ---------------------------------------------------------------------------

function getGaugeColor(score: number): string {
    if (score >= 7) return "var(--pg-red)";
    if (score >= 4) return "var(--pg-amber)";
    return "var(--pg-green)";
}

function getGaugeTextClass(score: number): string {
    if (score >= 7) return "text-[color:var(--pg-red)]";
    if (score >= 4) return "text-[color:var(--pg-amber)]";
    return "text-[color:var(--pg-green)]";
}

function useCountUp(value: number, durationMs = 700): number {
    const [displayValue, setDisplayValue] = useState(value);
    const previousValueRef = useRef(value);

    useEffect(() => {
        const startValue = previousValueRef.current;
        const delta = value - startValue;
        if (delta === 0) return;

        let frameId = 0;
        const startedAt = performance.now();
        const tick = (now: number) => {
            const progress = Math.min((now - startedAt) / durationMs, 1);
            const eased = 1 - Math.pow(1 - progress, 3);
            setDisplayValue(startValue + delta * eased);
            if (progress < 1) {
                frameId = requestAnimationFrame(tick);
            }
        };

        frameId = requestAnimationFrame(tick);
        previousValueRef.current = value;
        return () => cancelAnimationFrame(frameId);
    }, [value, durationMs]);

    return displayValue;
}

function RadialGauge({ score }: { score: number }) {
    const animatedScore = useCountUp(score);
    const r = 24;
    const circumference = 2 * Math.PI * r;
    const offset = circumference - (animatedScore / 10) * circumference;
    const color = getGaugeColor(animatedScore);
    const displayScore = Number.isInteger(score)
        ? Math.round(animatedScore).toString()
        : animatedScore.toFixed(1);

    return (
        <div className="relative w-16 h-16 flex-shrink-0">
            <svg viewBox="0 0 64 64" className="w-16 h-16" style={{ transform: "rotate(-90deg)" }}>
                <circle
                    cx="32"
                    cy="32"
                    r={r}
                    fill="none"
                    stroke="var(--border2)"
                    strokeWidth="5"
                />
                <circle
                    cx="32"
                    cy="32"
                    r={r}
                    fill="none"
                    stroke={color}
                    strokeWidth="5"
                    strokeLinecap="round"
                    strokeDasharray={circumference}
                    strokeDashoffset={offset}
                    style={{ filter: `drop-shadow(0 0 4px ${color})`, transition: "stroke-dashoffset 0.8s ease" }}
                />
            </svg>
            <div className="absolute inset-0 flex flex-col items-center justify-center">
                <span className={`text-[17px] font-bold font-mono leading-none ${getGaugeTextClass(animatedScore)}`}>
                    {displayScore}
                </span>
                <span className="text-[10px] text-muted-foreground leading-none">/10</span>
            </div>
        </div>
    );
}

// Noop token getter used when enrichment is disabled
const NOOP_TOKEN = async () => null;

export function IntelDashboard({
    iocs,
    attackType,
    confidence,
    riskScore = 1,
    riskScoreBreakdown,
    timeline = [],
    isLoading = false,
    getAccessToken,
    autoEnrichAll = false,
    onEnrichmentComplete,
}: IntelDashboardProps) {
    const highValueCount = iocs.filter((ioc) => ioc.is_high_value).length;
    const medValueCount = iocs.filter((ioc) => !ioc.is_high_value && (ioc.type === "btc" || ioc.type === "btc_wallet" || ioc.type === "url")).length;
    const lowValueCount = iocs.length - highValueCount - medValueCount;
    const { enrichmentStates, enrich, getKey } = useEnrichment(
        getAccessToken ?? NOOP_TOKEN,
    );
    const [expandedKeys, setExpandedKeys] = useState<Record<string, boolean>>({});
    const [copiedKey, setCopiedKey] = useState<string | null>(null);
    const [showAllTimeline, setShowAllTimeline] = useState(false);
    const [showBreakdown, setShowBreakdown] = useState(false);

    const copyToClipboard = async (value: string, copyKey: string) => {
        try {
            await navigator.clipboard.writeText(value);
            setCopiedKey(copyKey);
            setTimeout(() => setCopiedKey(null), 2000);
        } catch {
            // clipboard not available
        }
    };

    // Track which IOCs we've already tried to auto-enrich to avoid loops
    const autoEnrichedRef = useRef<Set<string>>(new Set());

    // US-040: Re-fetch risk score after any enrichment succeeds, so the
    // breakdown reflects updated IOC reputation multipliers.
    const prevEnrichStatesRef = useRef<Record<string, EnrichmentState>>({});
    const stableOnEnrichmentComplete = useCallback(() => {
        onEnrichmentComplete?.();
    }, [onEnrichmentComplete]);
    useEffect(() => {
        const newSuccesses = Object.entries(enrichmentStates).filter(
            ([key, state]) =>
                state.status === "success" &&
                prevEnrichStatesRef.current[key]?.status !== "success",
        );
        if (newSuccesses.length > 0) {
            stableOnEnrichmentComplete();
        }
        prevEnrichStatesRef.current = enrichmentStates;
    }, [enrichmentStates, stableOnEnrichmentComplete]);

    const toggleExpanded = (key: string) =>
        setExpandedKeys((prev) => ({ ...prev, [key]: !prev[key] }));

    // US-038/US-035: Auto-enrich IOCs when they first appear.
    // In live mode: BTC wallets and URLs (VirusTotal). In history mode (autoEnrichAll): all types,
    // so that previously cached enrichment results are restored immediately.
    useEffect(() => {
        if (!getAccessToken) return;

        iocs.forEach((ioc) => {
            const key = getKey(ioc.type, ioc.value);
            const shouldAutoEnrich = autoEnrichAll || ioc.type === "btc_wallet" || ioc.type === "url" || ioc.type === "ip";
            if (
                shouldAutoEnrich &&
                !autoEnrichedRef.current.has(key) &&
                !enrichmentStates[key]
            ) {
                autoEnrichedRef.current.add(key);
                enrich(ioc.type, ioc.value);
            }
        });
    }, [iocs, getAccessToken, enrich, getKey, enrichmentStates, autoEnrichAll]);

    // Group IOCs by type for display
    const groupedIocs = iocs.reduce<Record<string, ExtractedIOC[]>>((acc, ioc) => {
        const grpKey = ioc.type;
        if (!acc[grpKey]) acc[grpKey] = [];
        acc[grpKey].push(ioc);
        return acc;
    }, {});

    return (
        <div
            data-testid="intel-dashboard"
            className="rounded-lg border border-border/50 bg-card overflow-hidden"
        >
            {/* Header — sticky per wireframe */}
            <div className="sticky top-0 z-10 flex items-center justify-between px-5 py-4 border-b border-border bg-card">
                <div className="flex items-center gap-2">
                    <Shield className="h-3.5 w-3.5 text-primary" />
                    <h3 className="text-[13px] font-semibold text-foreground">
                        Threat Intel
                    </h3>
                </div>
                {isLoading && (
                    <div className="h-4 w-4 animate-spin rounded-full border-2 border-primary border-t-transparent" />
                )}
            </div>

            {/* Section 1: Attack Type */}
            {attackType && (
                <div
                    data-testid="attack-type-section"
                    className="px-5 py-4 border-b border-border"
                >
                    <div className="text-[10.5px] font-bold uppercase tracking-[0.1em] text-muted-foreground mb-2.5">
                        Attack Type
                    </div>
                    <div className="flex items-center justify-between">
                        <span className="text-sm font-semibold text-foreground">
                            {ATTACK_TYPE_LABELS[attackType] || attackType}
                        </span>
                        {confidence !== undefined && confidence > 0 && (
                            <span
                                data-testid="confidence-badge"
                                className="inline-flex items-center rounded-[4px] bg-[color:var(--pg-amber-dim)] px-2 py-[3px] text-[11px] font-semibold font-mono text-[color:var(--pg-amber)] border border-[color:var(--pg-amber)]"
                            >
                                {Math.round(confidence)}% conf.
                            </span>
                        )}
                    </div>
                </div>
            )}

            {/* Section 2: IOCs */}
            <div data-testid="ioc-section" className="px-5 py-4 border-b border-border">
                <div className="text-[10.5px] font-bold uppercase tracking-[0.1em] text-muted-foreground mb-2.5">
                    Collected IOCs
                </div>

                {/* Priority pills */}
                {iocs.length > 0 && (
                    <div className="flex flex-wrap gap-2 mb-3" data-testid="high-value-badge">
                        {highValueCount > 0 && (
                            <span className="inline-flex items-center gap-1.5 rounded-[4px] bg-[color:var(--pg-red-dim)] text-[color:var(--pg-red)] border border-[color:var(--pg-red)] px-2.5 py-1 text-[11.5px] font-medium font-mono">
                                {highValueCount} High
                            </span>
                        )}
                        {medValueCount > 0 && (
                            <span className="inline-flex items-center gap-1.5 rounded-[4px] bg-[color:var(--pg-accent-dim)] text-[color:var(--pg-accent)] border border-[color:var(--pg-accent)] px-2.5 py-1 text-[11.5px] font-medium font-mono">
                                {medValueCount} Med
                            </span>
                        )}
                        {lowValueCount > 0 && (
                            <span className="inline-flex items-center gap-1.5 rounded-[4px] bg-secondary text-secondary-foreground border border-border px-2.5 py-1 text-[11.5px] font-medium font-mono">
                                {lowValueCount} Low
                            </span>
                        )}
                    </div>
                )}

                {iocs.length === 0 ? (
                    <p className="text-sm text-muted-foreground text-center py-3 bg-muted/20 rounded-md">
                        No IOCs extracted yet.
                    </p>
                ) : (
                    <div className="relative">
                        <div className="space-y-3 max-h-64 overflow-y-auto pb-2">
                            {Object.entries(groupedIocs).map(([type, items]) => {
                                const groupLabel = IOC_LABELS[type] || type.toUpperCase();
                                return (
                                    <div key={type} className="space-y-2">
                                        <h4 className="text-[10.5px] font-bold uppercase tracking-[0.1em] text-muted-foreground">
                                            {groupLabel} ({items.length})
                                        </h4>
                                        {items.map((ioc, index) => {
                                            const Icon = IOC_ICONS[ioc.type] || Link;
                                            const label = IOC_LABELS[ioc.type] || ioc.type.toUpperCase();
                                            const key = getKey(ioc.type, ioc.value);
                                            const enrichState: EnrichmentState =
                                                enrichmentStates[key] ?? { status: "idle" };
                                            const isExpanded = expandedKeys[key] ?? false;
                                            const iconColors = getIocTypeIconColors(ioc.type);

                                            // Derive threat assessment when enrichment succeeded
                                            const assessment =
                                                enrichState.status === "success"
                                                    ? deriveThreatAssessment(enrichState.data)
                                                    : null;

                                            return (
                                                <div
                                                    key={ioc.id || `ioc-${index}`}
                                                    data-testid={`ioc-item-${ioc.type}`}
                                                    className="rounded-[5px] bg-secondary border border-border overflow-hidden animate-in fade-in slide-in-from-top-2 duration-300"
                                                >
                                                    {/* Card header: type icon + label/value + copy */}
                                                    <div className="flex items-center gap-2 px-3 py-2.5">
                                                        <div className={`w-[26px] h-[26px] rounded-[4px] flex items-center justify-center flex-shrink-0 border ${iconColors.bg} ${iconColors.border} ${iconColors.text}`}>
                                                            <Icon className="h-3 w-3" />
                                                        </div>
                                                        <div className="flex-1 min-w-0">
                                                            <div className="text-sm text-muted-foreground">{label}</div>
                                                            <div className="font-mono text-sm font-medium text-foreground break-all leading-snug">
                                                                {ioc.type === "url" ? defangUrl(ioc.value) : ioc.value}
                                                            </div>
                                                        </div>
                                                        <button
                                                            title="Copy to clipboard"
                                                            aria-label="Copy IOC value"
                                                            className="flex-shrink-0 p-1 rounded-[4px] text-muted-foreground hover:text-foreground hover:bg-border transition-colors"
                                                            onClick={() => copyToClipboard(ioc.value, key)}
                                                        >
                                                            {copiedKey === key ? (
                                                                <Check className="h-3 w-3 text-[color:var(--pg-green)]" />
                                                            ) : (
                                                                <Copy className="h-3 w-3" />
                                                            )}
                                                        </button>

                                                        {/* Enrich button — only shown when getAccessToken is provided and
                                                            not in autoEnrichAll mode where unsupported types silently skip */}
                                                        {getAccessToken && enrichState.status === "idle" && !autoEnrichAll && (
                                                            <button
                                                                data-testid={`enrich-button-${ioc.type}`}
                                                                className="flex items-center gap-1 rounded-[4px] border border-border bg-card px-2 py-1 text-[11px] font-medium text-muted-foreground hover:text-foreground hover:border-border transition-colors"
                                                                onClick={() => enrich(ioc.type, ioc.value)}
                                                            >
                                                                <Search className="h-3 w-3" />
                                                                Enrich
                                                            </button>
                                                        )}

                                                        {/* Loading spinner */}
                                                        {enrichState.status === "loading" && (
                                                            <div
                                                                data-testid={`enrich-loading-${ioc.type}`}
                                                                className="flex items-center gap-1 px-2 py-1 text-[11px] text-muted-foreground"
                                                            >
                                                                <Loader2 className="h-3 w-3 animate-spin" />
                                                                <span>Enriching...</span>
                                                            </div>
                                                        )}
                                                    </div>

                                                    {/* Card footer: enrichment results */}
                                                    {enrichState.status === "success" && assessment && (
                                                        <div data-testid={`enrichment-result-${ioc.type}`}>
                                                            <div className="flex items-center justify-between gap-2 px-3 py-[7px] bg-background border-t border-border">
                                                                {/* Left: status dot + reputation */}
                                                                <div className="flex items-center gap-1.5">
                                                                    {(() => {
                                                                        const badge = getReputationBadge(assessment.reputation);
                                                                        return (
                                                                            <>
                                                                                <div className={`w-1.5 h-1.5 rounded-full ${badge.dotClass}`} />
                                                                                <span
                                                                                    data-testid={`reputation-badge-${ioc.type}`}
                                                                                    className={`text-[11px] font-semibold tracking-wide ${badge.className}`}
                                                                                >
                                                                                    {badge.label}
                                                                                </span>
                                                                            </>
                                                                        );
                                                                    })()}
                                                                </div>

                                                                {/* Right: threat score + cached + refresh */}
                                                                <div className="flex items-center gap-1.5">
                                                                    <span
                                                                        data-testid={`threat-score-${ioc.type}`}
                                                                        className={`text-[11px] font-medium font-mono tabular-nums ${getThreatScoreColor(assessment.threat_score)}`}
                                                                    >
                                                                        {assessment.threat_score}
                                                                        <span className="text-muted-foreground/60">/100</span>
                                                                    </span>

                                                                    {/* Cached indicator */}
                                                                    {enrichState.data.cached && (
                                                                        <span
                                                                            data-testid={`cached-badge-${ioc.type}`}
                                                                            title="Result from cache"
                                                                            className="inline-flex items-center justify-center"
                                                                        >
                                                                            <BadgeCheck className="h-3 w-3 text-muted-foreground/50" />
                                                                        </span>
                                                                    )}

                                                                    {/* Refresh button */}
                                                                    <button
                                                                        data-testid={`refresh-button-${ioc.type}`}
                                                                        title="Force refresh (bypass cache)"
                                                                        aria-label="Refresh enrichment"
                                                                        className="p-[3px] text-muted-foreground hover:text-foreground transition-colors"
                                                                        onClick={() => enrich(ioc.type, ioc.value, true)}
                                                                    >
                                                                        <RefreshCw className="h-[11px] w-[11px]" />
                                                                    </button>
                                                                </div>
                                                            </div>

                                                            {/* Expandable raw data */}
                                                            {enrichState.data.payload && (
                                                                <div className="px-3 py-1.5 border-t border-border">
                                                                    <button
                                                                        data-testid={`expand-raw-${ioc.type}`}
                                                                        aria-label={isExpanded ? "Hide raw data" : "Show raw data"}
                                                                        className="flex items-center gap-1.5 text-[11.5px] text-muted-foreground hover:text-foreground transition-colors"
                                                                        onClick={() => toggleExpanded(key)}
                                                                    >
                                                                        {isExpanded ? (
                                                                            <ChevronUp className="h-[11px] w-[11px]" />
                                                                        ) : (
                                                                            <ChevronDown className="h-[11px] w-[11px]" />
                                                                        )}
                                                                        {isExpanded ? "Hide" : "Show"} raw data
                                                                    </button>
                                                                    {isExpanded && (
                                                                        <>
                                                                            <div className="mt-1 text-[10px] text-muted-foreground/50">
                                                                                via {enrichState.data.source} &middot; {enrichState.data.latency_ms}ms
                                                                            </div>
                                                                            <pre
                                                                                data-testid={`raw-data-${ioc.type}`}
                                                                                className="mt-2 p-2.5 rounded-[4px] bg-background border border-border font-mono text-[10.5px] text-secondary-foreground leading-relaxed max-h-32 overflow-auto break-all"
                                                                            >
                                                                                {JSON.stringify(enrichState.data.payload, null, 2)}
                                                                            </pre>
                                                                        </>
                                                                    )}
                                                                </div>
                                                            )}
                                                        </div>
                                                    )}

                                                    {/* Error state with retry */}
                                                    {enrichState.status === "error" &&
                                                        !(autoEnrichAll && enrichState.error === "Unsupported IOC type") && (
                                                        <div
                                                            data-testid={`enrichment-error-${ioc.type}`}
                                                            className="flex items-center gap-2 px-3 py-2 border-t border-border bg-background"
                                                        >
                                                            <AlertCircle className="h-3.5 w-3.5 text-[color:var(--pg-red)] flex-shrink-0" />
                                                            <span className="text-[11px] text-[color:var(--pg-red)] flex-1 truncate">
                                                                {enrichState.error}
                                                            </span>
                                                            <button
                                                                data-testid={`retry-button-${ioc.type}`}
                                                                className="flex items-center gap-1 rounded-[4px] border border-border bg-card px-2 py-0.5 text-[11px] font-medium text-muted-foreground hover:text-foreground transition-colors"
                                                                onClick={() => enrich(ioc.type, ioc.value)}
                                                            >
                                                                <RefreshCw className="h-3 w-3" />
                                                                Retry
                                                            </button>
                                                        </div>
                                                    )}
                                                </div>
                                            );
                                        })}
                                    </div>
                                );
                            })}
                        </div>
                        {iocs.length > 5 && (
                            <div className="pointer-events-none absolute bottom-0 left-0 right-0 h-8 bg-gradient-to-t from-card to-transparent" />
                        )}
                    </div>
                )}
            </div>

            {/* Section 3: Risk Score (US-032 Enhanced with breakdown) */}
            <div data-testid="risk-score-section" className="px-5 py-4 border-b border-border">
                <div className="text-[10.5px] font-bold uppercase tracking-[0.1em] text-muted-foreground mb-2.5">
                    Risk Score
                </div>

                {/* Use enhanced breakdown if available, otherwise fall back to radial gauge */}
                {riskScoreBreakdown ? (
                    <>
                        {/* Gauge + summary always visible */}
                        <div className="flex items-center gap-4">
                            <RadialGauge score={riskScoreBreakdown.total_score} />
                            <div className="flex-1">
                                <div className={`text-[13px] font-semibold uppercase ${getGaugeTextClass(riskScoreBreakdown.total_score)}`}>
                                    {getRiskLabel(riskScoreBreakdown.total_score)} Risk
                                </div>
                                <p className="text-xs text-muted-foreground mt-1 leading-relaxed">
                                    {riskScoreBreakdown.components.length} risk components analyzed.
                                </p>
                                <button
                                    onClick={() => setShowBreakdown(!showBreakdown)}
                                    className="inline-flex items-center gap-1 text-[11.5px] text-muted-foreground hover:text-foreground transition-colors mt-1.5"
                                >
                                    Details
                                    <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" className="w-[11px] h-[11px]">
                                        <path d="M6 4l4 4-4 4" />
                                    </svg>
                                </button>
                            </div>
                        </div>
                        {showBreakdown && (
                            <div className="mt-3">
                                <RiskScoreBreakdown
                                    breakdown={riskScoreBreakdown}
                                    isLoading={isLoading}
                                    hasUnenrichedIOCs={getAccessToken != null && iocs.some(
                                        (ioc) => {
                                            const state = enrichmentStates[getKey(ioc.type, ioc.value)];
                                            return !state || state.status === "error";
                                        }
                                    )}
                                />
                            </div>
                        )}
                    </>
                ) : (
                    <div className="flex items-center gap-4">
                        <RadialGauge score={riskScore} />
                        <div className="flex-1" data-testid="risk-score-value">
                            <div className={`text-[13px] font-semibold uppercase ${getGaugeTextClass(riskScore)}`}>
                                {getRiskLabel(riskScore)} Risk
                            </div>
                            <p className="text-xs text-muted-foreground mt-1 leading-relaxed">
                                Risk assessment based on attack indicators and engagement patterns.
                            </p>
                        </div>
                    </div>
                )}
            </div>

            {/* Section 4: Timeline */}
            <div data-testid="timeline-section" className="px-5 py-4">
                <div className="text-[10.5px] font-bold uppercase tracking-[0.1em] text-muted-foreground mb-2.5">
                    Extraction Timeline
                </div>

                {timeline.length === 0 ? (
                    <p className="text-sm text-muted-foreground text-center py-3 bg-muted/20 rounded-md">
                        No events yet.
                    </p>
                ) : (
                    <>
                        <div className="max-h-48 overflow-y-auto">
                            <div className="flex flex-col">
                                {(showAllTimeline ? timeline : timeline.slice(0, 5)).map((event, index, arr) => {
                                    const eventTime = new Date(event.timestamp);
                                    const timeAgo = formatDistanceToNow(eventTime, { addSuffix: true });
                                    const isLast = index === arr.length - 1;
                                    const isActive = event.is_high_value;

                                    return (
                                        <div
                                            key={event.ioc_id || `event-${index}`}
                                            data-testid="timeline-event"
                                            className="flex gap-3 relative"
                                            style={{ paddingBottom: isLast ? 0 : "14px" }}
                                        >
                                            {/* Connector line */}
                                            {!isLast && (
                                                <div
                                                    className="absolute w-px bg-border"
                                                    style={{ left: "7px", top: "22px", bottom: 0 }}
                                                />
                                            )}
                                            {/* Dot */}
                                            <div
                                                className={`w-[15px] h-[15px] rounded-full border-2 flex items-center justify-center flex-shrink-0 mt-0.5 ${
                                                    isActive
                                                        ? "border-[color:var(--pg-green)] bg-[color:var(--pg-green-dim)]"
                                                        : "border-border bg-secondary"
                                                }`}
                                            >
                                                <div
                                                    className={`w-[5px] h-[5px] rounded-full ${
                                                        isActive
                                                            ? "bg-[color:var(--pg-green)]"
                                                            : "bg-muted-foreground"
                                                    }`}
                                                />
                                            </div>
                                            {/* Content */}
                                            <div>
                                                <p className={`text-[13px] font-medium ${isActive ? "text-[color:var(--pg-green)]" : "text-foreground"}`}>
                                                    {event.description}
                                                </p>
                                                <p className="text-[11.5px] text-muted-foreground mt-0.5">
                                                    {timeAgo}
                                                    <span className="mx-1">&middot;</span>
                                                    <span title={eventTime.toLocaleString()}>
                                                        {eventTime.toLocaleDateString("en-GB", { day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit" })}
                                                    </span>
                                                </p>
                                            </div>
                                        </div>
                                    );
                                })}
                            </div>
                        </div>
                        {!showAllTimeline && timeline.length > 5 && (
                            <button
                                onClick={() => setShowAllTimeline(true)}
                                className="mt-2 w-full text-center text-xs font-medium text-primary hover:text-primary/80 transition-colors py-1"
                            >
                                View all ({timeline.length} events)
                            </button>
                        )}
                        {showAllTimeline && timeline.length > 5 && (
                            <button
                                onClick={() => setShowAllTimeline(false)}
                                className="mt-2 w-full text-center text-xs font-medium text-primary hover:text-primary/80 transition-colors py-1"
                            >
                                Show less
                            </button>
                        )}
                    </>
                )}
            </div>
        </div>
    );
}
