"use client";

import { formatDistanceToNow } from "date-fns";
import { MessageSquare, Calendar, AlertTriangle, User } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { SessionHistoryItem } from "@/types/schemas";
import { cn } from "@/lib/utils";
import { ATTACK_TYPE_COLORS, getRiskScoreColor, getRiskLabel } from "@/lib/constants/ioc";

interface SessionHistoryListProps {
    sessions: SessionHistoryItem[];
    onSessionClick: (sessionId: string) => void;
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
                    role="button"
                    tabIndex={0}
                    onClick={() => onSessionClick(session.session_id)}
                    onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); onSessionClick(session.session_id); } }}
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
                                    {getRiskLabel(session.risk_score)} ({session.risk_score}/10)
                                </span>
                            </div>
                        </div>
                    </CardContent>
                </Card>
            ))}
        </div>
    );
}
