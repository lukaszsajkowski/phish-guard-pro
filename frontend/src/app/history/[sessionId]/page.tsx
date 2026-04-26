"use client";

import { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import { useRouter, useParams } from "next/navigation";
import { createClient } from "@supabase/supabase-js";
import { Shield } from "lucide-react";
import { AuthenticatedLayout } from "@/components/app/AuthenticatedLayout";
import { SessionDetailSkeleton } from "@/components/app/LoadingSkeletons";
import { SessionDetailHeader, ReadOnlyChatArea, PhishingEmailCard } from "@/components/history";
import { PersonaCard } from "@/components/dashboard/PersonaCard";
import { IntelDashboard } from "@/components/dashboard/IntelDashboard";
import { ApiError } from "@/components/app/ApiError";
import { Button } from "@/components/ui/button";
import {
    Sheet,
    SheetContent,
    SheetHeader,
    SheetTitle,
    SheetTrigger,
} from "@/components/ui/sheet";
import { ChatMessage, ExtractedIOC, Persona, TimelineEvent, RiskScoreBreakdown } from "@/types/schemas";
import { toast } from "sonner";

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

    // US-040: Standalone intel re-fetch so enrichment can trigger a risk score refresh.
    const fetchIntelDashboard = useCallback(async () => {
        try {
            const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL;
            const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;
            if (!supabaseUrl || !supabaseAnonKey) return;
            const sb = createClient(supabaseUrl, supabaseAnonKey);
            const { data: { session } } = await sb.auth.getSession();
            if (!session?.access_token) return;
            const resp = await fetch(
                `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/v1/intel/dashboard/${sessionId}`,
                { headers: { Authorization: `Bearer ${session.access_token}` } }
            );
            if (resp.ok) {
                const intelData = await resp.json();
                if (intelData.risk_score_breakdown) setRiskScoreBreakdown(intelData.risk_score_breakdown);
                setRiskScore(intelData.risk_score || 1);
            }
        } catch {
            // non-critical — enrichment re-fetch failures are silent
        }
    }, [sessionId]);

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

            const filename = `phishguard_session_${new Date().toISOString().slice(0, 10)}.json`;
            const blob = await response.blob();
            const url = URL.createObjectURL(blob);
            const a = document.createElement("a");
            a.href = url;
            a.download = filename;
            a.click();
            URL.revokeObjectURL(url);
            toast.success(`Exported ${filename}`);
        } catch (err) {
            console.error("Error exporting JSON:", err);
            toast.error("JSON export failed", { description: err instanceof Error ? err.message : "Please try again." });
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

            const filename = `phishguard_iocs_${new Date().toISOString().slice(0, 10)}.csv`;
            const blob = await response.blob();
            const url = URL.createObjectURL(blob);
            const a = document.createElement("a");
            a.href = url;
            a.download = filename;
            a.click();
            URL.revokeObjectURL(url);
            toast.success(`Exported ${filename}`);
        } catch (err) {
            console.error("Error exporting CSV:", err);
            toast.error("CSV export failed", { description: err instanceof Error ? err.message : "Please try again." });
        } finally {
            setIsExporting(false);
        }
    };

    const handleExportStix = async () => {
        setIsExporting(true);
        try {
            const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL;
            const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;
            if (!supabaseUrl || !supabaseAnonKey) return;

            const supabase = createClient(supabaseUrl, supabaseAnonKey);
            const { data: { session } } = await supabase.auth.getSession();
            if (!session?.access_token) return;

            const response = await fetch(
                `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/v1/session/${sessionId}/export/stix`,
                {
                    headers: { Authorization: `Bearer ${session.access_token}` },
                }
            );

            if (!response.ok) {
                throw new Error("Failed to export STIX 2.1");
            }

            const filename = `phishguard_iocs_${new Date().toISOString().slice(0, 10)}.stix.json`;
            const blob = await response.blob();
            const url = URL.createObjectURL(blob);
            const a = document.createElement("a");
            a.href = url;
            a.download = filename;
            a.click();
            URL.revokeObjectURL(url);
            toast.success(`Exported ${filename}`);
        } catch (err) {
            console.error("Error exporting STIX:", err);
            toast.error("STIX export failed", { description: err instanceof Error ? err.message : "Please try again." });
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

    // Not found state
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
                <SessionDetailSkeleton />
            ) : (
                <div className="flex flex-col h-screen overflow-hidden">
                    {/* Error state */}
                    {error && (
                        <div className="p-4">
                            <ApiError
                                title="Failed to Load Session"
                                message={error}
                                onRetry={handleRetry}
                                isRetrying={isRetrying}
                            />
                        </div>
                    )}

                    {/* Session content */}
                    {sessionData && !error && (
                        <>
                            {/* Top bar — full width */}
                            <SessionDetailHeader
                                attackType={sessionData.attack_type}
                                attackTypeDisplay={sessionData.attack_type_display}
                                createdAt={sessionData.created_at || new Date().toISOString()}
                                status={sessionData.status}
                                turnCount={sessionData.turn_count}
                                onExportJson={handleExportJson}
                                onExportCsv={handleExportCsv}
                                onExportStix={handleExportStix}
                                isExporting={isExporting}
                            />

                            {/* Content area — center column + right panel */}
                            <div className="flex flex-1 overflow-hidden">
                                {/* Center column — scrollable */}
                                <div className="flex-1 overflow-y-auto px-4 lg:px-7 py-6 flex flex-col gap-5 min-w-0">
                                    {/* Mobile-only intel panel trigger */}
                                    <div className="lg:hidden">
                                        <Sheet>
                                            <SheetTrigger asChild>
                                                <Button variant="outline" className="w-full gap-2">
                                                    <Shield className="h-4 w-4" />
                                                    Threat Intel ({sessionData.iocs.length} IOCs)
                                                </Button>
                                            </SheetTrigger>
                                            <SheetContent side="right" className="w-[340px] sm:w-[380px] p-0 overflow-y-auto">
                                                <SheetHeader className="sr-only">
                                                    <SheetTitle>Threat Intelligence</SheetTitle>
                                                </SheetHeader>
                                                <IntelDashboard
                                                    iocs={sessionData.iocs}
                                                    attackType={sessionData.attack_type}
                                                    confidence={sessionData.confidence}
                                                    riskScore={calculateFallbackRiskScore()}
                                                    riskScoreBreakdown={riskScoreBreakdown}
                                                    timeline={timeline}
                                                    getAccessToken={getAccessToken}
                                                    autoEnrichAll
                                                    onEnrichmentComplete={fetchIntelDashboard}
                                                />
                                            </SheetContent>
                                        </Sheet>
                                    </div>

                                    {/* Persona card */}
                                    {sessionData.persona && (
                                        <PersonaCard persona={sessionData.persona} />
                                    )}

                                    {/* Phishing email card */}
                                    {sessionData.original_email && (
                                        <PhishingEmailCard
                                            emailContent={sessionData.original_email}
                                        />
                                    )}

                                    {/* Conversation history */}
                                    <ReadOnlyChatArea
                                        messages={messages}
                                        personaName={sessionData.persona?.name}
                                    />
                                </div>

                                {/* Right panel — fixed width, scrollable, hidden on mobile */}
                                <aside className="hidden lg:block w-[320px] shrink-0 border-l border-border bg-surface overflow-y-auto">
                                    <IntelDashboard
                                        iocs={sessionData.iocs}
                                        attackType={sessionData.attack_type}
                                        confidence={sessionData.confidence}
                                        riskScore={calculateFallbackRiskScore()}
                                        riskScoreBreakdown={riskScoreBreakdown}
                                        timeline={timeline}
                                        getAccessToken={getAccessToken}
                                        autoEnrichAll
                                        onEnrichmentComplete={fetchIntelDashboard}
                                    />
                                </aside>
                            </div>
                        </>
                    )}
                </div>
            )}
        </AuthenticatedLayout>
    );
}
