"use client";

import { useState, useEffect, useRef } from "react";
import { formatDistanceToNow } from "date-fns";
import {
    AlertCircle,
    AlertTriangle,
    Shield,
    Target,
    Clock,
    TrendingUp,
    Link,
    Search,
    Loader2,
    ChevronDown,
    ChevronUp,
    RefreshCw,
    BadgeCheck,
} from "lucide-react";
import { ExtractedIOC, TimelineEvent, RiskScoreBreakdown as RiskScoreBreakdownType, EnrichmentState, ReputationLabel } from "@/types/schemas";
import {
    IOC_ICONS,
    IOC_LABELS,
    ATTACK_TYPE_LABELS,
    getRiskScoreColor,
    getRiskScoreBg,
    getRiskLabel,
    getRiskScoreBarColor,
} from "@/lib/constants/ioc";
import { RiskScoreBreakdown } from "./RiskScoreBreakdown";
import { useEnrichment, deriveThreatAssessment } from "@/hooks/useEnrichment";

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
}

// ---------------------------------------------------------------------------
// Threat-score colour helpers (0-100 scale)
// ---------------------------------------------------------------------------

function getThreatScoreColor(score: number): string {
    if (score <= 33) return "text-green-500";
    if (score <= 66) return "text-yellow-500";
    return "text-red-500";
}

function getThreatScoreBg(score: number): string {
    if (score <= 33) return "bg-green-500";
    if (score <= 66) return "bg-yellow-500";
    return "bg-red-500";
}

function getReputationBadge(reputation: ReputationLabel) {
    const map: Record<ReputationLabel, { label: string; className: string }> = {
        malicious: {
            label: "Malicious",
            className: "bg-red-500/10 text-red-500",
        },
        suspicious: {
            label: "Suspicious",
            className: "bg-yellow-500/10 text-yellow-500",
        },
        clean: {
            label: "Clean",
            className: "bg-green-500/10 text-green-500",
        },
        unknown: {
            label: "Unknown",
            className: "bg-muted text-muted-foreground",
        },
    };
    return map[reputation] ?? map.unknown;
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
}: IntelDashboardProps) {
    const highValueCount = iocs.filter((ioc) => ioc.is_high_value).length;
    const { enrichmentStates, enrich, getKey } = useEnrichment(
        getAccessToken ?? NOOP_TOKEN,
    );
    const [expandedKeys, setExpandedKeys] = useState<Record<string, boolean>>({});

    // Track which IOCs we've already tried to auto-enrich to avoid loops
    const autoEnrichedRef = useRef<Set<string>>(new Set());

    const toggleExpanded = (key: string) =>
        setExpandedKeys((prev) => ({ ...prev, [key]: !prev[key] }));

    // US-038: Auto-enrich IOCs when they first appear.
    // In live mode: only BTC wallets. In history mode (autoEnrichAll): all types,
    // so that previously cached enrichment results are restored immediately.
    useEffect(() => {
        if (!getAccessToken) return;

        iocs.forEach((ioc) => {
            const key = getKey(ioc.type, ioc.value);
            const shouldAutoEnrich = autoEnrichAll || ioc.type === "btc_wallet";
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

    return (
        <div
            data-testid="intel-dashboard"
            className="rounded-lg border border-border/50 bg-card p-4 space-y-4"
        >
            {/* Header */}
            <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                    <Shield className="h-5 w-5 text-primary" />
                    <h3 className="text-sm font-semibold text-foreground">
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
                    className="rounded-md bg-muted/30 p-3"
                >
                    <div className="flex items-center gap-2 mb-2">
                        <Target className="h-4 w-4 text-muted-foreground" />
                        <span className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
                            Attack Type
                        </span>
                    </div>
                    <div className="flex items-center justify-between">
                        <span className="text-sm font-semibold text-foreground">
                            {ATTACK_TYPE_LABELS[attackType] || attackType}
                        </span>
                        {confidence !== undefined && confidence > 0 && (
                            <span
                                data-testid="confidence-badge"
                                className="inline-flex items-center rounded-full bg-primary/10 px-2 py-0.5 text-xs font-medium text-primary"
                            >
                                {Math.round(confidence)}% confidence
                            </span>
                        )}
                    </div>
                </div>
            )}

            {/* Section 2: IOCs */}
            <div data-testid="ioc-section">
                <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-2">
                        <AlertTriangle className="h-4 w-4 text-muted-foreground" />
                        <span className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
                            Collected IOCs
                        </span>
                    </div>
                    <div className="flex items-center gap-2">
                        {highValueCount > 0 && (
                            <span
                                data-testid="high-value-badge"
                                className="inline-flex items-center gap-1 rounded-full bg-red-500/10 px-2 py-0.5 text-xs font-medium text-red-500"
                            >
                                <TrendingUp className="h-3 w-3" />
                                {highValueCount} High Value
                            </span>
                        )}
                        <span className="text-xs text-muted-foreground">
                            {iocs.length} IOC{iocs.length !== 1 ? "s" : ""}
                        </span>
                    </div>
                </div>

                {iocs.length === 0 ? (
                    <p className="text-sm text-muted-foreground text-center py-3 bg-muted/20 rounded-md">
                        No IOCs extracted yet.
                    </p>
                ) : (
                    <div className="space-y-2 max-h-64 overflow-y-auto">
                        {iocs.map((ioc, index) => {
                            const Icon = IOC_ICONS[ioc.type] || Link;
                            const label = IOC_LABELS[ioc.type] || ioc.type.toUpperCase();
                            const isHighValue = ioc.is_high_value;
                            const key = getKey(ioc.type, ioc.value);
                            const enrichState: EnrichmentState =
                                enrichmentStates[key] ?? { status: "idle" };
                            const isExpanded = expandedKeys[key] ?? false;

                            // Derive threat assessment when enrichment succeeded
                            const assessment =
                                enrichState.status === "success"
                                    ? deriveThreatAssessment(enrichState.data)
                                    : null;

                            return (
                                <div
                                    key={ioc.id || `ioc-${index}`}
                                    data-testid={`ioc-item-${ioc.type}`}
                                    className={`rounded-md p-2 text-sm ${isHighValue
                                        ? "bg-red-500/5 border border-red-500/20"
                                        : "bg-muted/30"
                                        }`}
                                >
                                    {/* Row 1: icon + label + value + enrich button */}
                                    <div className="flex items-start gap-2">
                                        <Icon
                                            className={`h-4 w-4 mt-0.5 flex-shrink-0 ${isHighValue
                                                ? "text-red-500"
                                                : "text-muted-foreground"
                                                }`}
                                        />
                                        <div className="flex-1 min-w-0">
                                            <div className="flex items-center gap-2">
                                                <span
                                                    className={`text-xs font-medium ${isHighValue
                                                        ? "text-red-500"
                                                        : "text-muted-foreground"
                                                        }`}
                                                >
                                                    {label}
                                                </span>
                                            </div>
                                            <p
                                                className={`font-mono text-xs break-all ${isHighValue
                                                    ? "text-red-400"
                                                    : "text-foreground"
                                                    }`}
                                            >
                                                {ioc.value}
                                            </p>
                                        </div>

                                        {/* Enrich button — only shown when getAccessToken is provided and
                                            not in autoEnrichAll mode where unsupported types silently skip */}
                                        {getAccessToken && enrichState.status === "idle" && !autoEnrichAll && (
                                            <button
                                                data-testid={`enrich-button-${ioc.type}`}
                                                className="flex items-center gap-1 rounded-md border border-border/50 bg-background px-2 py-1 text-xs font-medium text-muted-foreground hover:text-foreground hover:border-border transition-colors"
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
                                                className="flex items-center gap-1 px-2 py-1 text-xs text-muted-foreground"
                                            >
                                                <Loader2 className="h-3 w-3 animate-spin" />
                                                <span>Enriching...</span>
                                            </div>
                                        )}
                                    </div>

                                    {/* Row 2: Enrichment results */}
                                    {enrichState.status === "success" && assessment && (
                                        <div
                                            data-testid={`enrichment-result-${ioc.type}`}
                                            className="mt-2 space-y-2 border-t border-border/30 pt-2"
                                        >
                                            <div className="flex items-center gap-3 flex-wrap">
                                                {/* Threat score */}
                                                <div
                                                    data-testid={`threat-score-${ioc.type}`}
                                                    className="flex items-center gap-1.5"
                                                >
                                                    <span className={`text-lg font-bold ${getThreatScoreColor(assessment.threat_score)}`}>
                                                        {assessment.threat_score}
                                                    </span>
                                                    <div className="flex flex-col">
                                                        <span className="text-[10px] text-muted-foreground leading-tight">
                                                            /100
                                                        </span>
                                                        <div className="h-1 w-10 rounded-full bg-muted/40 overflow-hidden">
                                                            <div
                                                                className={`h-full transition-all ${getThreatScoreBg(assessment.threat_score)}`}
                                                                style={{ width: `${assessment.threat_score}%` }}
                                                            />
                                                        </div>
                                                    </div>
                                                </div>

                                                {/* Reputation badge */}
                                                {(() => {
                                                    const badge = getReputationBadge(assessment.reputation);
                                                    return (
                                                        <span
                                                            data-testid={`reputation-badge-${ioc.type}`}
                                                            className={`inline-flex items-center rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide ${badge.className}`}
                                                        >
                                                            {badge.label}
                                                        </span>
                                                    );
                                                })()}

                                                {/* Cached indicator */}
                                                {enrichState.data.cached && (
                                                    <span
                                                        data-testid={`cached-badge-${ioc.type}`}
                                                        className="inline-flex items-center gap-0.5 rounded-full bg-blue-500/10 px-2 py-0.5 text-[10px] font-medium text-blue-500"
                                                    >
                                                        <BadgeCheck className="h-3 w-3" />
                                                        Cached
                                                    </span>
                                                )}

                                                {/* Refresh button */}
                                                <button
                                                    data-testid={`refresh-button-${ioc.type}`}
                                                    title="Force refresh (bypass cache)"
                                                    className="inline-flex items-center justify-center rounded-md p-1 text-muted-foreground hover:bg-muted/50 hover:text-foreground transition-colors"
                                                    onClick={() => enrich(ioc.type, ioc.value, true)}
                                                >
                                                    <RefreshCw className="h-3 w-3" />
                                                </button>

                                                {/* Source + latency */}
                                                <span className="text-[10px] text-muted-foreground ml-auto">
                                                    {enrichState.data.source} &middot; {enrichState.data.latency_ms}ms
                                                </span>
                                            </div>

                                            {/* Expandable raw data */}
                                            {enrichState.data.payload && (
                                                <div>
                                                    <button
                                                        data-testid={`expand-raw-${ioc.type}`}
                                                        className="flex items-center gap-1 text-[10px] text-muted-foreground hover:text-foreground transition-colors"
                                                        onClick={() => toggleExpanded(key)}
                                                    >
                                                        {isExpanded ? (
                                                            <ChevronUp className="h-3 w-3" />
                                                        ) : (
                                                            <ChevronDown className="h-3 w-3" />
                                                        )}
                                                        {isExpanded ? "Hide" : "Show"} raw data
                                                    </button>
                                                    {isExpanded && (
                                                        <pre
                                                            data-testid={`raw-data-${ioc.type}`}
                                                            className="mt-1 max-h-32 overflow-auto rounded-md bg-muted/40 p-2 text-[10px] font-mono text-muted-foreground"
                                                        >
                                                            {JSON.stringify(enrichState.data.payload, null, 2)}
                                                        </pre>
                                                    )}
                                                </div>
                                            )}
                                        </div>
                                    )}

                                    {/* Row 2 (error): Error state with retry.
                                        In autoEnrichAll mode, "Unsupported IOC type" is expected for
                                        non-BTC IOCs — suppress the error to keep the view clean. */}
                                    {enrichState.status === "error" &&
                                        !(autoEnrichAll && enrichState.error === "Unsupported IOC type") && (
                                        <div
                                            data-testid={`enrichment-error-${ioc.type}`}
                                            className="mt-2 flex items-center gap-2 border-t border-border/30 pt-2"
                                        >
                                            <AlertCircle className="h-3.5 w-3.5 text-red-500 flex-shrink-0" />
                                            <span className="text-xs text-red-500 flex-1 truncate">
                                                {enrichState.error}
                                            </span>
                                            <button
                                                data-testid={`retry-button-${ioc.type}`}
                                                className="flex items-center gap-1 rounded-md border border-border/50 bg-background px-2 py-0.5 text-[10px] font-medium text-muted-foreground hover:text-foreground transition-colors"
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
                )}
            </div>

            {/* Section 3: Risk Score (US-032 Enhanced with breakdown) */}
            <div data-testid="risk-score-section">
                <div className="flex items-center gap-2 mb-2">
                    <AlertCircle className="h-4 w-4 text-muted-foreground" />
                    <span className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
                        Risk Score
                    </span>
                </div>

                {/* Use enhanced breakdown if available, otherwise fall back to simple display */}
                {riskScoreBreakdown ? (
                    <RiskScoreBreakdown
                        breakdown={riskScoreBreakdown}
                        isLoading={isLoading}
                    />
                ) : (
                    <div className="flex items-center gap-3">
                        <div
                            data-testid="risk-score-value"
                            className={`text-3xl font-bold ${getRiskScoreColor(riskScore)}`}
                        >
                            {riskScore}
                        </div>
                        <div className="flex-1">
                            <div className="flex items-center justify-between text-xs mb-1">
                                <span className={`font-medium ${getRiskScoreColor(riskScore)}`}>
                                    {getRiskLabel(riskScore)} Risk
                                </span>
                                <span className="text-muted-foreground">/10</span>
                            </div>
                            <div className="h-2 bg-muted/30 rounded-full overflow-hidden">
                                <div
                                    data-testid="risk-score-bar"
                                    className={`h-full transition-all duration-500 ${getRiskScoreBarColor(riskScore)}`}
                                    style={{ width: `${(riskScore / 10) * 100}%` }}
                                />
                            </div>
                        </div>
                    </div>
                )}
            </div>

            {/* Section 4: Timeline */}
            <div data-testid="timeline-section">
                <div className="flex items-center gap-2 mb-2">
                    <Clock className="h-4 w-4 text-muted-foreground" />
                    <span className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
                        Extraction Timeline
                    </span>
                </div>

                {timeline.length === 0 ? (
                    <p className="text-sm text-muted-foreground text-center py-3 bg-muted/20 rounded-md">
                        No events yet.
                    </p>
                ) : (
                    <div className="space-y-2 max-h-32 overflow-y-auto">
                        {timeline.map((event, index) => {
                            const eventTime = new Date(event.timestamp);
                            const timeAgo = formatDistanceToNow(eventTime, { addSuffix: true });

                            return (
                                <div
                                    key={event.ioc_id || `event-${index}`}
                                    data-testid="timeline-event"
                                    className={`flex items-start gap-2 text-xs p-2 rounded-md ${event.is_high_value
                                        ? "bg-red-500/5 border-l-2 border-red-500"
                                        : "bg-muted/20 border-l-2 border-muted"
                                        }`}
                                >
                                    <div className="flex-1">
                                        <p className={`${event.is_high_value ? "text-red-500" : "text-foreground"}`}>
                                            {event.description}
                                        </p>
                                        <p className="text-muted-foreground mt-0.5">
                                            {timeAgo}
                                        </p>
                                    </div>
                                </div>
                            );
                        })}
                    </div>
                )}
            </div>
        </div>
    );
}
