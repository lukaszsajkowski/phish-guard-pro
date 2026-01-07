"use client";

import {
    Download,
    FileJson,
    FileSpreadsheet,
    Clock,
    MessageSquare,
    Shield,
    Target,
    TrendingUp,
    Bitcoin,
    Building2,
    Phone,
    Link,
    RefreshCw,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

interface IOCSummary {
    id: string;
    ioc_type: string;
    value: string;
    is_high_value: boolean;
    timestamp: string;
}

interface SessionSummaryData {
    session_id: string;
    exchange_count: number;
    session_start: string;
    session_end: string;
    attack_type: string;
    attack_type_display: string;
    attack_confidence: number;
    iocs: IOCSummary[];
    total_responses: number;
    duration_seconds: number;
    formatted_duration: string;
    risk_score: number;
    high_value_ioc_count: number;
}

interface SessionSummaryProps {
    summary: SessionSummaryData;
    onExportJson: () => void;
    onExportCsv: () => void;
    onNewSession: () => void;
    isExporting?: boolean;
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

/**
 * SessionSummary - Displays the final session report (US-018)
 *
 * Shows:
 * - Number of exchanges, duration, attack type
 * - All collected IOCs
 * - Safety Score (% safe responses)
 * - Export buttons (JSON, CSV)
 * - "New session" button
 */
export function SessionSummary({
    summary,
    onExportJson,
    onExportCsv,
    onNewSession,
    isExporting = false,
}: SessionSummaryProps) {
    return (
        <div className="max-w-4xl mx-auto p-6 space-y-6" data-testid="session-summary">
            {/* Header */}
            <div className="text-center space-y-2">
                <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-primary/10 mb-4">
                    <Target className="w-8 h-8 text-primary" />
                </div>
                <h1 className="text-2xl font-bold">Session Complete</h1>
                <p className="text-muted-foreground">
                    Here's a summary of your phishing simulation session
                </p>
            </div>

            {/* Stats Grid */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                {/* Exchanges */}
                <div className="p-4 rounded-lg bg-muted/30 border border-border/50">
                    <div className="flex items-center gap-2 mb-2">
                        <MessageSquare className="w-4 h-4 text-muted-foreground" />
                        <span className="text-sm text-muted-foreground">Exchanges</span>
                    </div>
                    <p className="text-2xl font-bold" data-testid="exchange-count">
                        {summary.exchange_count}
                    </p>
                </div>

                {/* Duration */}
                <div className="p-4 rounded-lg bg-muted/30 border border-border/50">
                    <div className="flex items-center gap-2 mb-2">
                        <Clock className="w-4 h-4 text-muted-foreground" />
                        <span className="text-sm text-muted-foreground">Duration</span>
                    </div>
                    <p className="text-2xl font-bold" data-testid="duration">
                        {summary.formatted_duration}
                    </p>
                </div>

                {/* IOCs Found */}
                <div className="p-4 rounded-lg bg-muted/30 border border-border/50">
                    <div className="flex items-center gap-2 mb-2">
                        <TrendingUp className="w-4 h-4 text-muted-foreground" />
                        <span className="text-sm text-muted-foreground">IOCs Found</span>
                    </div>
                    <p className="text-2xl font-bold" data-testid="ioc-count">
                        {summary.iocs.length}
                        {summary.high_value_ioc_count > 0 && (
                            <span className="text-sm font-normal text-red-500 ml-1">
                                ({summary.high_value_ioc_count} high-value)
                            </span>
                        )}
                    </p>
                </div>

                {/* Risk Score */}
                <div className="p-4 rounded-lg bg-muted/30 border border-border/50">
                    <div className="flex items-center gap-2 mb-2">
                        <Shield className="w-4 h-4 text-muted-foreground" />
                        <span className="text-sm text-muted-foreground">Risk Score</span>
                    </div>
                    <p
                        className={cn(
                            "text-2xl font-bold",
                            summary.risk_score >= 7
                                ? "text-red-500"
                                : summary.risk_score >= 4
                                    ? "text-yellow-500"
                                    : "text-green-500"
                        )}
                        data-testid="risk-score"
                    >
                        {summary.risk_score}/10
                    </p>
                </div>
            </div>

            {/* Attack Type */}
            <div className="p-4 rounded-lg bg-muted/30 border border-border/50">
                <h3 className="font-semibold mb-2">Attack Type</h3>
                <p className="text-lg" data-testid="attack-type">
                    {summary.attack_type_display}
                </p>
                {summary.attack_confidence > 0 && (
                    <p className="text-sm text-muted-foreground">
                        Confidence: {Math.round(summary.attack_confidence)}%
                    </p>
                )}
            </div>

            {/* Collected IOCs */}
            {summary.iocs.length > 0 && (
                <div className="p-4 rounded-lg bg-muted/30 border border-border/50">
                    <h3 className="font-semibold mb-4">Collected Indicators of Compromise</h3>
                    <div className="space-y-2">
                        {summary.iocs.map((ioc) => {
                            const IconComponent = IOC_ICONS[ioc.ioc_type] || Link;
                            const label = IOC_LABELS[ioc.ioc_type] || ioc.ioc_type.toUpperCase();
                            return (
                                <div
                                    key={ioc.id}
                                    className={cn(
                                        "flex items-center gap-3 p-2 rounded-md",
                                        ioc.is_high_value ? "bg-red-500/10" : "bg-muted/50"
                                    )}
                                    data-testid={`ioc-item-${ioc.ioc_type}`}
                                >
                                    <IconComponent
                                        className={cn(
                                            "w-4 h-4 flex-shrink-0",
                                            ioc.is_high_value ? "text-red-500" : "text-muted-foreground"
                                        )}
                                    />
                                    <div className="min-w-0 flex-1">
                                        <p className="text-xs text-muted-foreground">{label}</p>
                                        <p className="font-mono text-sm truncate">{ioc.value}</p>
                                    </div>
                                    {ioc.is_high_value && (
                                        <span className="text-xs font-medium text-red-500 px-2 py-0.5 bg-red-500/10 rounded">
                                            High Value
                                        </span>
                                    )}
                                </div>
                            );
                        })}
                    </div>
                </div>
            )}

            {/* Export and New Session Buttons */}
            <div className="flex flex-col sm:flex-row gap-3 pt-4 border-t border-border/50">
                <Button
                    variant="outline"
                    onClick={onExportJson}
                    disabled={isExporting}
                    className="flex-1"
                    data-testid="export-json-button"
                >
                    <FileJson className="w-4 h-4 mr-2" />
                    Export JSON
                </Button>
                <Button
                    variant="outline"
                    onClick={onExportCsv}
                    disabled={isExporting || summary.iocs.length === 0}
                    className="flex-1"
                    data-testid="export-csv-button"
                >
                    <FileSpreadsheet className="w-4 h-4 mr-2" />
                    Export IOC (CSV)
                </Button>
                <Button
                    onClick={onNewSession}
                    className="flex-1"
                    data-testid="new-session-button"
                >
                    <RefreshCw className="w-4 h-4 mr-2" />
                    New Session
                </Button>
            </div>
        </div>
    );
}
