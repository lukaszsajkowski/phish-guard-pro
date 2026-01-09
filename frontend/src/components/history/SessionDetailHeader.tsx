"use client";

import Link from "next/link";
import { format } from "date-fns";
import { ArrowLeft, MessageSquare, Calendar } from "lucide-react";
import { cn } from "@/lib/utils";

interface SessionDetailHeaderProps {
    attackType: string;
    attackTypeDisplay: string;
    createdAt: string;
    status: string;
    turnCount: number;
}

// Attack type badge colors (matching SessionHistoryList)
const ATTACK_TYPE_COLORS: Record<string, string> = {
    nigerian_419: "bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-400",
    ceo_fraud: "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400",
    fake_invoice: "bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400",
    romance_scam: "bg-pink-100 text-pink-700 dark:bg-pink-900/30 dark:text-pink-400",
    tech_support: "bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-400",
    lottery_prize: "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400",
    crypto_investment: "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400",
    delivery_scam: "bg-teal-100 text-teal-700 dark:bg-teal-900/30 dark:text-teal-400",
    not_phishing: "bg-gray-100 text-gray-700 dark:bg-gray-900/30 dark:text-gray-400",
};

// Status badge colors
const STATUS_COLORS: Record<string, string> = {
    active: "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400",
    archived: "bg-gray-100 text-gray-700 dark:bg-gray-900/30 dark:text-gray-400",
    completed: "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400",
};

function formatCreatedAt(dateString: string): string {
    try {
        const date = new Date(dateString);
        return format(date, "PPp"); // e.g., "Jan 9, 2026, 2:30 PM"
    } catch {
        return "Unknown date";
    }
}

function formatStatus(status: string): string {
    return status.charAt(0).toUpperCase() + status.slice(1);
}

export function SessionDetailHeader({
    attackType,
    attackTypeDisplay,
    createdAt,
    status,
    turnCount,
}: SessionDetailHeaderProps) {
    return (
        <div className="space-y-4" data-testid="session-detail-header">
            {/* Back link */}
            <Link
                href="/history"
                className="inline-flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground transition-colors"
                data-testid="back-to-history-link"
            >
                <ArrowLeft className="h-4 w-4" />
                <span>Back to history</span>
            </Link>

            {/* Session metadata */}
            <div className="flex flex-wrap items-center gap-3">
                {/* Attack type badge */}
                <span
                    className={cn(
                        "inline-flex items-center px-3 py-1 rounded-full text-sm font-medium",
                        ATTACK_TYPE_COLORS[attackType] ||
                            ATTACK_TYPE_COLORS["not_phishing"]
                    )}
                    data-testid="attack-type-badge"
                >
                    {attackTypeDisplay}
                </span>

                {/* Status badge */}
                <span
                    className={cn(
                        "inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium",
                        STATUS_COLORS[status] || STATUS_COLORS["archived"]
                    )}
                    data-testid="status-badge"
                >
                    {formatStatus(status)}
                </span>

                {/* Turn count */}
                <span className="flex items-center gap-1.5 text-sm text-muted-foreground">
                    <MessageSquare className="h-4 w-4" />
                    <span data-testid="turn-count">
                        {turnCount} {turnCount === 1 ? "turn" : "turns"}
                    </span>
                </span>

                {/* Created date */}
                <span className="flex items-center gap-1.5 text-sm text-muted-foreground">
                    <Calendar className="h-4 w-4" />
                    <span data-testid="created-at">{formatCreatedAt(createdAt)}</span>
                </span>
            </div>
        </div>
    );
}
