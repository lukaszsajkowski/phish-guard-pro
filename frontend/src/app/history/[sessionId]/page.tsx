"use client";

import { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import { useRouter, useParams } from "next/navigation";
import { createClient } from "@supabase/supabase-js";
import { Loader2, Download, FileJson, FileSpreadsheet } from "lucide-react";
import { AuthenticatedLayout } from "@/components/app/AuthenticatedLayout";
import { Button } from "@/components/ui/button";
import { SessionDetailHeader, ReadOnlyChatArea } from "@/components/history";
import { PersonaCard } from "@/components/dashboard/PersonaCard";
import { IntelDashboard } from "@/components/dashboard/IntelDashboard";
import { ApiError } from "@/components/app/ApiError";
import { ChatMessage, ExtractedIOC, Persona, TimelineEvent, RiskScoreBreakdown } from "@/types/schemas";

// API response type for session restore
interface SessionRestoreResponse {
    session_id: string;
    status: string;
    attack_type: string;
    attack_type_display: string;
    confidence: number;
    persona: Persona | null;
    original_email: string | null;
    messages: Array<{
        id: string;
        sender: "bot" | "scammer";
        content: string;
        timestamp: string;
        thinking?: {
            turn_goal: string;
            selected_tactic: string;
            reasoning: string;
        };
    }>;
    iocs: ExtractedIOC[];
    turn_count: number;
    turn_limit: number;
    is_at_limit: boolean;
    created_at?: string;
}

export default function SessionDetailPage() {
    const router = useRouter();
    const params = useParams();
    const sessionId = params.sessionId as string;

    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [isRetrying, setIsRetrying] = useState(false);
    const [notFound, setNotFound] = useState(false);

    // Session data
    const [sessionData, setSessionData] = useState<SessionRestoreResponse | null>(null);
    const [messages, setMessages] = useState<ChatMessage[]>([]);
    const [timeline, setTimeline] = useState<TimelineEvent[]>([]);
    const [riskScoreBreakdown, setRiskScoreBreakdown] = useState<RiskScoreBreakdown | undefined>();
    const [riskScore, setRiskScore] = useState<number>(1);

    // Export state (US-030)
    const [isExporting, setIsExporting] = useState(false);

    // Stable callback for enrichment hook to obtain a JWT (US-038)
    const getAccessToken = useCallback(async (): Promise<string | null> => {
        const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL;
        const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;
        if (!supabaseUrl || !supabaseAnonKey) return null;
        const sb = createClient(supabaseUrl, supabaseAnonKey);
        const { data: { session } } = await sb.auth.getSession();
        return session?.access_token ?? null;
    }, []);

    // Fetch session data from API
    const fetchSessionData = useCallback(async () => {
        setError(null);
        setNotFound(false);

        try {
            const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL;
            const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;

            if (!supabaseUrl || !supabaseAnonKey) {
                throw new Error("Supabase configuration missing");
            }

            const supabase = createClient(supabaseUrl, supabaseAnonKey);
            const { data: { session } } = await supabase.auth.getSession();

            if (!session?.access_token) {
                router.push("/login");
                return;
            }

            const response = await fetch(
                `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/v1/session/${sessionId}/restore`,
                {
                    headers: {
                        Authorization: `Bearer ${session.access_token}`,
                    },
                }
            );

            if (!response.ok) {
                if (response.status === 401) {
                    router.push("/login");
                    return;
                }
                if (response.status === 404) {
                    setNotFound(true);
                    return;
                }
                const errorData = await response.json().catch(() => ({}));
                throw new Error(errorData.error || errorData.detail || "Failed to fetch session");
            }

            const data: SessionRestoreResponse = await response.json();
            setSessionData(data);

            // Transform messages to ChatMessage format
            const transformedMessages: ChatMessage[] = data.messages.map((msg) => ({
                id: msg.id,
                sender: msg.sender,
                content: msg.content,
                timestamp: new Date(msg.timestamp),
                thinking: msg.thinking,
            }));
            setMessages(transformedMessages);

            // Create timeline from IOCs
            const iocTimeline: TimelineEvent[] = data.iocs
                .filter((ioc) => ioc.created_at)
                .map((ioc) => ({
                    timestamp: ioc.created_at!,
                    event_type: "ioc_extracted" as const,
                    description: `Extracted ${ioc.type.toUpperCase()}: ${ioc.value}`,
                    ioc_id: ioc.id,
                    is_high_value: ioc.is_high_value,
                }))
                .sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime());
            setTimeline(iocTimeline);

            // Fetch intel dashboard data for risk score breakdown (US-032)
            try {
                const intelResponse = await fetch(
                    `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/v1/intel/dashboard/${sessionId}`,
                    {
                        headers: {
                            Authorization: `Bearer ${session.access_token}`,
                        },
                    }
                );

                if (intelResponse.ok) {
                    const intelData = await intelResponse.json();
                    if (intelData.risk_score_breakdown) {
                        setRiskScoreBreakdown(intelData.risk_score_breakdown);
                    }
                    setRiskScore(intelData.risk_score || 1);
                }
            } catch (intelError) {
                console.warn("Failed to fetch intel dashboard data:", intelError);
                // Fall back to calculated risk score
            }
        } catch (err) {
            console.error("Error fetching session:", err);
            setError(err instanceof Error ? err.message : "Failed to load session");
        } finally {
            setIsLoading(false);
        }
    }, [sessionId, router]);

    // Initial fetch
    useEffect(() => {
        fetchSessionData();
    }, [fetchSessionData]);

    const handleRetry = async () => {
        setIsRetrying(true);
        await fetchSessionData();
        setIsRetrying(false);
    };

    // Export handlers (US-030)
    const handleExportJson = async () => {
        setIsExporting(true);
        try {
            const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL;
            const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;
            if (!supabaseUrl || !supabaseAnonKey) return;

            const supabase = createClient(supabaseUrl, supabaseAnonKey);
            const { data: { session } } = await supabase.auth.getSession();
            if (!session?.access_token) return;

            const response = await fetch(
                `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/v1/session/${sessionId}/export/json`,
                {
                    headers: { Authorization: `Bearer ${session.access_token}` },
                }
            );

            if (!response.ok) {
                throw new Error("Failed to export JSON");
            }

            const blob = await response.blob();
            const url = URL.createObjectURL(blob);
            const a = document.createElement("a");
            a.href = url;
            a.download = `phishguard_session_${new Date().toISOString().slice(0, 10)}.json`;
            a.click();
            URL.revokeObjectURL(url);
        } catch (err) {
            console.error("Error exporting JSON:", err);
        } finally {
            setIsExporting(false);
        }
    };

    const handleExportCsv = async () => {
        setIsExporting(true);
        try {
            const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL;
            const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;
            if (!supabaseUrl || !supabaseAnonKey) return;

            const supabase = createClient(supabaseUrl, supabaseAnonKey);
            const { data: { session } } = await supabase.auth.getSession();
            if (!session?.access_token) return;

            const response = await fetch(
                `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/v1/session/${sessionId}/export/csv`,
                {
                    headers: { Authorization: `Bearer ${session.access_token}` },
                }
            );

            if (!response.ok) {
                throw new Error("Failed to export CSV");
            }

            const blob = await response.blob();
            const url = URL.createObjectURL(blob);
            const a = document.createElement("a");
            a.href = url;
            a.download = `phishguard_iocs_${new Date().toISOString().slice(0, 10)}.csv`;
            a.click();
            URL.revokeObjectURL(url);
        } catch (err) {
            console.error("Error exporting CSV:", err);
        } finally {
            setIsExporting(false);
        }
    };

    // Fallback risk score calculation (used when API doesn't return breakdown)
    const calculateFallbackRiskScore = (): number => {
        if (!sessionData) return riskScore || 1;
        if (riskScore > 1) return riskScore; // Use API score if available
        const highValueCount = sessionData.iocs.filter((ioc) => ioc.is_high_value).length;
        const totalCount = sessionData.iocs.length;
        return Math.min(10, 1 + highValueCount * 2 + (totalCount - highValueCount));
    };

    const handleNewSession = () => {
        router.push("/dashboard");
    };

    // Not found state - show outside layout since we may not be authenticated
    if (notFound && !isLoading) {
        return (
            <AuthenticatedLayout onNewSession={handleNewSession}>
                <main className="flex flex-1 flex-col items-center justify-center p-6">
                    <div className="text-center max-w-md">
                        <h1 className="text-2xl font-bold tracking-tight mb-2">
                            Session Not Found
                        </h1>
                        <p className="text-muted-foreground mb-6">
                            The session you&apos;re looking for doesn&apos;t exist or you don&apos;t have
                            permission to view it.
                        </p>
                        <Link
                            href="/history"
                            className="inline-flex items-center justify-center rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground shadow transition-colors hover:bg-primary/90"
                        >
                            Back to History
                        </Link>
                    </div>
                </main>
            </AuthenticatedLayout>
        );
    }

    return (
        <AuthenticatedLayout onNewSession={handleNewSession}>
            {isLoading ? (
                <div className="flex flex-1 items-center justify-center">
                    <div className="flex items-center gap-3">
                        <Loader2 className="h-6 w-6 animate-spin text-primary" />
                        <span className="text-muted-foreground">Loading session...</span>
                    </div>
                </div>
            ) : (
                <main className="flex flex-1 flex-col p-6">
                    <div className="max-w-6xl mx-auto w-full space-y-6">
                        {/* Error state */}
                        {error && (
                            <ApiError
                                title="Failed to Load Session"
                                message={error}
                                onRetry={handleRetry}
                                isRetrying={isRetrying}
                            />
                        )}

                        {/* Session content */}
                        {sessionData && !error && (
                            <>
                                {/* Header */}
                                <SessionDetailHeader
                                    attackType={sessionData.attack_type}
                                    attackTypeDisplay={sessionData.attack_type_display}
                                    createdAt={sessionData.created_at || new Date().toISOString()}
                                    status={sessionData.status}
                                    turnCount={sessionData.turn_count}
                                />

                                {/* Export buttons (US-030) */}
                                <div className="flex flex-col sm:flex-row sm:items-center gap-3 p-4 rounded-lg border border-border/50 bg-card">
                                    <div className="flex items-center gap-3 flex-1">
                                        <Download className="h-5 w-5 text-muted-foreground flex-shrink-0" />
                                        <span className="text-sm font-medium">Export Session Data</span>
                                    </div>
                                    <div className="flex gap-2">
                                    <Button
                                        variant="outline"
                                        size="sm"
                                        onClick={handleExportJson}
                                        disabled={isExporting}
                                        data-testid="export-json-button"
                                    >
                                        {isExporting ? (
                                            <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                                        ) : (
                                            <FileJson className="h-4 w-4 mr-2" />
                                        )}
                                        Export JSON
                                    </Button>
                                    <Button
                                        variant="outline"
                                        size="sm"
                                        onClick={handleExportCsv}
                                        disabled={isExporting}
                                        data-testid="export-csv-button"
                                    >
                                        {isExporting ? (
                                            <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                                        ) : (
                                            <FileSpreadsheet className="h-4 w-4 mr-2" />
                                        )}
                                        Export CSV
                                    </Button>
                                    </div>
                                </div>

                                {/* Main content grid - US-026 responsive */}
                                <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
                                    {/* Left column - Conversation */}
                                    <div className="xl:col-span-2 space-y-6">
                                        {/* Persona card */}
                                        {sessionData.persona && (
                                            <PersonaCard persona={sessionData.persona} />
                                        )}

                                        {/* Original email preview (if available) */}
                                        {sessionData.original_email && (
                                            <div className="rounded-lg border border-border/50 bg-card p-4">
                                                <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-wide mb-3">
                                                    Original Phishing Email
                                                </h3>
                                                <div className="bg-muted/30 rounded-md p-4 text-sm whitespace-pre-wrap break-words max-h-48 overflow-y-auto">
                                                    {sessionData.original_email}
                                                </div>
                                            </div>
                                        )}

                                        {/* Conversation history */}
                                        <div className="rounded-lg border border-border/50 bg-card p-4 min-h-[400px]">
                                            <ReadOnlyChatArea messages={messages} />
                                        </div>
                                    </div>

                                    {/* Right column - Intel Dashboard */}
                                    <div className="xl:col-span-1">
                                        <div className="sticky top-6">
                                            <IntelDashboard
                                                iocs={sessionData.iocs}
                                                attackType={sessionData.attack_type}
                                                confidence={sessionData.confidence}
                                                riskScore={calculateFallbackRiskScore()}
                                                riskScoreBreakdown={riskScoreBreakdown}
                                                timeline={timeline}
                                                getAccessToken={getAccessToken}
                                            />
                                        </div>
                                    </div>
                                </div>
                            </>
                        )}
                    </div>
                </main>
            )}
        </AuthenticatedLayout>
    );
}
