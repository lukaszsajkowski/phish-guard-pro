"use client";

import { formatDistanceToNow } from "date-fns";
import { MessageSquare, Calendar, AlertTriangle, User } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { SessionHistoryItem } from "@/types/schemas";
import { cn } from "@/lib/utils";

interface SessionHistoryListProps {
    sessions: SessionHistoryItem[];
    onSessionClick: (sessionId: string) => void;
}

// Attack type badge colors
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

function getRiskScoreColor(riskScore: number): string {
    if (riskScore <= 3) {
        return "text-green-600 dark:text-green-400";
    }
    if (riskScore <= 6) {
        return "text-yellow-600 dark:text-yellow-400";
    }
    return "text-red-600 dark:text-red-400";
}

function getRiskScoreLabel(riskScore: number): string {
    if (riskScore <= 3) {
        return "Low";
    }
    if (riskScore <= 6) {
        return "Medium";
    }
    return "High";
}

function formatCreatedAt(dateString: string): string {
    try {
        const date = new Date(dateString);
        return formatDistanceToNow(date, { addSuffix: true });
    } catch {
        return "Unknown date";
    }
}

export function SessionHistoryList({ sessions, onSessionClick }: SessionHistoryListProps) {
    return (
        <div className="space-y-3" data-testid="session-history-list">
            {sessions.map((session) => (
                <Card
                    key={session.session_id}
                    className="cursor-pointer transition-all hover:border-primary/50 hover:shadow-md"
                    onClick={() => onSessionClick(session.session_id)}
                    data-testid={`session-row-${session.session_id}`}
                >
                    <CardContent className="py-4">
                        <div className="flex flex-col sm:flex-row sm:items-center gap-3 sm:gap-4">
                            {/* Attack type badge */}
                            <span
                                className={cn(
                                    "inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium w-fit",
                                    ATTACK_TYPE_COLORS[session.attack_type || "not_phishing"] ||
                                        ATTACK_TYPE_COLORS["not_phishing"]
                                )}
                                data-testid="attack-type-badge"
                            >
                                {session.attack_type_display}
                            </span>

                            {/* Session details */}
                            <div className="flex-1 min-w-0">
                                <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-sm text-muted-foreground">
                                    {/* Persona name */}
                                    {session.persona_name && (
                                        <span className="flex items-center gap-1">
                                            <User className="h-3.5 w-3.5" />
                                            <span className="truncate max-w-[150px]">
                                                {session.persona_name}
                                            </span>
                                        </span>
                                    )}

                                    {/* Turn count */}
                                    <span className="flex items-center gap-1">
                                        <MessageSquare className="h-3.5 w-3.5" />
                                        <span>
                                            {session.turn_count} {session.turn_count === 1 ? "turn" : "turns"}
                                        </span>
                                    </span>

                                    {/* Created date */}
                                    <span className="flex items-center gap-1">
                                        <Calendar className="h-3.5 w-3.5" />
                                        <span>{formatCreatedAt(session.created_at)}</span>
                                    </span>
                                </div>
                            </div>

                            {/* Risk score indicator */}
                            <div
                                className={cn(
                                    "flex items-center gap-1.5 text-sm font-medium",
                                    getRiskScoreColor(session.risk_score)
                                )}
                                data-testid="risk-score"
                            >
                                <AlertTriangle className="h-4 w-4" />
                                <span>
                                    {getRiskScoreLabel(session.risk_score)} ({session.risk_score}/10)
                                </span>
                            </div>
                        </div>
                    </CardContent>
                </Card>
            ))}
        </div>
    );
}
