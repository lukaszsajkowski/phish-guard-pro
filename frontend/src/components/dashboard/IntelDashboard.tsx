"use client";

import { formatDistanceToNow } from "date-fns";
import {
    Bitcoin,
    Building2,
    Phone,
    Link,
    AlertTriangle,
    Shield,
    Target,
    Clock,
    Gauge,
    TrendingUp,
} from "lucide-react";
import { ExtractedIOC, TimelineEvent } from "@/types/schemas";

interface IntelDashboardProps {
    iocs: ExtractedIOC[];
    attackType?: string;
    confidence?: number;
    riskScore?: number;
    timeline?: TimelineEvent[];
    isLoading?: boolean;
}

const IOC_ICONS: Record<string, React.ElementType> = {
    btc: Bitcoin,
    btc_wallet: Bitcoin,
    iban: Building2,
    phone: Phone,
    url: Link,
};

const IOC_LABELS: Record<string, string> = {
    btc: "BTC Wallet",
    btc_wallet: "BTC Wallet",
    iban: "IBAN",
    phone: "Phone",
    url: "URL",
};

const ATTACK_TYPE_LABELS: Record<string, string> = {
    nigerian_419: "Nigerian 419 Scam",
    ceo_fraud: "CEO Fraud",
    fake_invoice: "Fake Invoice",
    romance_scam: "Romance Scam",
    tech_support: "Tech Support Scam",
    lottery_prize: "Lottery/Prize Scam",
    crypto_investment: "Crypto Investment Scam",
    delivery_scam: "Delivery Scam",
    not_phishing: "Not Phishing",
};

function getRiskScoreColor(score: number): string {
    if (score <= 3) return "text-green-500";
    if (score <= 6) return "text-yellow-500";
    return "text-red-500";
}

function getRiskScoreBg(score: number): string {
    if (score <= 3) return "bg-green-500/10";
    if (score <= 6) return "bg-yellow-500/10";
    return "bg-red-500/10";
}

function getRiskLabel(score: number): string {
    if (score <= 3) return "Low";
    if (score <= 6) return "Medium";
    return "High";
}

export function IntelDashboard({
    iocs,
    attackType,
    confidence,
    riskScore = 1,
    timeline = [],
    isLoading = false,
}: IntelDashboardProps) {
    const highValueCount = iocs.filter((ioc) => ioc.is_high_value).length;

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
                    <div className="space-y-2 max-h-48 overflow-y-auto">
                        {iocs.map((ioc, index) => {
                            const Icon = IOC_ICONS[ioc.type] || Link;
                            const label = IOC_LABELS[ioc.type] || ioc.type.toUpperCase();
                            const isHighValue = ioc.is_high_value;

                            return (
                                <div
                                    key={ioc.id || `ioc-${index}`}
                                    data-testid={`ioc-item-${ioc.type}`}
                                    className={`flex items-start gap-2 rounded-md p-2 text-sm ${isHighValue
                                        ? "bg-red-500/5 border border-red-500/20"
                                        : "bg-muted/30"
                                        }`}
                                >
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
                                </div>
                            );
                        })}
                    </div>
                )}
            </div>

            {/* Section 3: Risk Score */}
            <div
                data-testid="risk-score-section"
                className={`rounded-md p-3 ${getRiskScoreBg(riskScore)}`}
            >
                <div className="flex items-center gap-2 mb-2">
                    <Gauge className="h-4 w-4 text-muted-foreground" />
                    <span className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
                        Risk Score
                    </span>
                </div>
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
                                className={`h-full transition-all duration-500 ${riskScore <= 3
                                    ? "bg-green-500"
                                    : riskScore <= 6
                                        ? "bg-yellow-500"
                                        : "bg-red-500"
                                    }`}
                                style={{ width: `${(riskScore / 10) * 100}%` }}
                            />
                        </div>
                    </div>
                </div>
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
