"use client";

import {
    Bitcoin,
    Building2,
    Phone,
    Link,
    AlertTriangle,
    Shield,
} from "lucide-react";
import { ExtractedIOC } from "@/types/schemas";

interface IntelDashboardProps {
    iocs: ExtractedIOC[];
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

export function IntelDashboard({ iocs, isLoading = false }: IntelDashboardProps) {
    const highValueCount = iocs.filter((ioc) => ioc.is_high_value).length;

    if (iocs.length === 0 && !isLoading) {
        return (
            <div
                data-testid="intel-dashboard"
                className="rounded-lg border border-border/50 bg-card p-4"
            >
                <div className="flex items-center gap-2 mb-3">
                    <Shield className="h-5 w-5 text-muted-foreground" />
                    <h3 className="text-sm font-semibold text-foreground">
                        Threat Intel
                    </h3>
                </div>
                <p className="text-sm text-muted-foreground text-center py-4">
                    No IOCs extracted yet. Submit a scammer message to begin collecting threat intelligence.
                </p>
            </div>
        );
    }

    return (
        <div
            data-testid="intel-dashboard"
            className="rounded-lg border border-border/50 bg-card p-4"
        >
            {/* Header */}
            <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-2">
                    <Shield className="h-5 w-5 text-primary" />
                    <h3 className="text-sm font-semibold text-foreground">
                        Threat Intel
                    </h3>
                </div>
                <div className="flex items-center gap-2">
                    {highValueCount > 0 && (
                        <span
                            data-testid="high-value-badge"
                            className="inline-flex items-center gap-1 rounded-full bg-red-500/10 px-2 py-0.5 text-xs font-medium text-red-500"
                        >
                            <AlertTriangle className="h-3 w-3" />
                            {highValueCount} High Value
                        </span>
                    )}
                    <span className="text-xs text-muted-foreground">
                        {iocs.length} IOC{iocs.length !== 1 ? "s" : ""}
                    </span>
                </div>
            </div>

            {/* IOC List */}
            <div className="space-y-2 max-h-64 overflow-y-auto">
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
                                {ioc.context && (
                                    <p className="text-xs text-muted-foreground mt-1 truncate">
                                        {ioc.context}
                                    </p>
                                )}
                            </div>
                        </div>
                    );
                })}
            </div>

            {isLoading && (
                <div className="flex justify-center py-2">
                    <div className="h-4 w-4 animate-spin rounded-full border-2 border-primary border-t-transparent" />
                </div>
            )}
        </div>
    );
}
