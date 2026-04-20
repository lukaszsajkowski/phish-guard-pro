"use client";

import { useEffect, useState, useCallback, Suspense, useRef, type ComponentProps } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { Loader2, PanelRightClose, PanelRightOpen } from "lucide-react";
import { createClient, User } from "@supabase/supabase-js";
import { EmailInput } from "@/components/app/email-input";
import { ClassificationResult, type AttackType } from "@/components/app/ClassificationResult";
import { ApiError } from "@/components/app/ApiError";
import { AppHeader } from "@/components/app/AppHeader";
import { AuthenticatedLayout } from "@/components/app/AuthenticatedLayout";
import { PersonaCard } from "@/components/dashboard/PersonaCard";
import { ChatArea } from "@/components/dashboard/ChatArea";
import { IntelDashboard } from "@/components/dashboard/IntelDashboard";
import { SessionLimitDialog } from "@/components/dashboard/SessionLimitDialog";
import { UnmaskingDialog } from "@/components/dashboard/UnmaskingDialog";
import { EndSessionDialog } from "@/components/dashboard/EndSessionDialog";
import { SessionSummary } from "@/components/dashboard/SessionSummary";
import { Persona, ChatMessage, ExtractedIOC, TimelineEvent, RiskScoreBreakdown, AgentThinking } from "@/types/schemas";
import { Button } from "@/components/ui/button";
import { useMediaQuery } from "@/hooks/useMediaQuery";

import {
    AlertDialog,
    AlertDialogAction,
    AlertDialogCancel,
    AlertDialogContent,
    AlertDialogDescription,
    AlertDialogFooter,
    AlertDialogHeader,
    AlertDialogTitle,
} from "@/components/ui/alert-dialog";

// Wrapper component for Suspense boundary (required for useSearchParams in Next.js 16)
export default function DashboardPage() {
    return (
        <Suspense fallback={
            <div className="flex min-h-screen items-center justify-center bg-background">
                <div className="flex items-center gap-3">
                    <Loader2 className="h-6 w-6 animate-spin text-primary" />
                    <span className="text-muted-foreground">Loading...</span>
                </div>
            </div>
        }>
            <DashboardContent />
        </Suspense>
    );
}

function DashboardContent() {
    const router = useRouter();
    const [user, setUser] = useState<User | null>(null);
    const [emailContent, setEmailContent] = useState("");
    const [showSafeWarning, setShowSafeWarning] = useState(false);
    const [sessionId, setSessionId] = useState<string | null>(null);
    const [isGenerating, setIsGenerating] = useState(false);
    const [messages, setMessages] = useState<ChatMessage[]>([]);
    const [classificationResult, setClassificationResult] = useState<{
        attackType: AttackType;
        confidence: number;
        reasoning: string;
        persona?: Persona;
    } | null>(null);
    const [extractedIOCs, setExtractedIOCs] = useState<ExtractedIOC[]>([]);
    const [timelineEvents, setTimelineEvents] = useState<TimelineEvent[]>([]);
    const [riskScoreBreakdown, setRiskScoreBreakdown] = useState<RiskScoreBreakdown | undefined>();
    const [riskScore, setRiskScore] = useState<number>(1);
    // Turn count and limit state (US-015)
    const [turnCount, setTurnCount] = useState(0);
    const [turnLimit, setTurnLimit] = useState(20);
    const [showSessionLimitDialog, setShowSessionLimitDialog] = useState(false);
    const [isExtendingSession, setIsExtendingSession] = useState(false);
    // Unmasking detection state (US-016)
    const [showUnmaskingDialog, setShowUnmaskingDialog] = useState(false);
    const [unmaskingPhrases, setUnmaskingPhrases] = useState<string[]>([]);
    const [unmaskingConfidence, setUnmaskingConfidence] = useState(0);
    // Session end state (US-017)
    const [showEndSessionDialog, setShowEndSessionDialog] = useState(false);
    const [isEndingSession, setIsEndingSession] = useState(false);
    // Session summary state (US-018)
    const [showSummary, setShowSummary] = useState(false);
    const [sessionSummary, setSessionSummary] = useState<ComponentProps<typeof SessionSummary>["summary"] | null>(null);
    const [isExporting, setIsExporting] = useState(false);
    // API Error state (US-022)
    const [analysisError, setAnalysisError] = useState<string | null>(null);
    const [isRetryingAnalysis, setIsRetryingAnalysis] = useState(false);
    const [generationError, setGenerationError] = useState<string | null>(null);
    // Fallback model state (US-023)
    const [usedFallbackModel, setUsedFallbackModel] = useState(false);
    // New Session state (US-025)
    const [showNewSessionDialog, setShowNewSessionDialog] = useState(false);
    // Side panel collapse state (US-026)
    const [isSidePanelCollapsed, setIsSidePanelCollapsed] = useState(false);
    // Session restoration state (US-031)
    const [isRestoringSession, setIsRestoringSession] = useState(false);
    const searchParams = useSearchParams();
    // Ref to track intentional session clearing (prevents restore effect from re-restoring)
    const isClearingSessionRef = useRef(false);

    // Responsive side panel collapse (US-026)
    const isLargeScreen = useMediaQuery("(min-width: 1280px)");

    // Stable callback for enrichment hook to obtain a JWT (US-038)
    const getAccessToken = useCallback(async (): Promise<string | null> => {
        const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL;
        const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;
        if (!supabaseUrl || !supabaseAnonKey) return null;
        const sb = createClient(supabaseUrl, supabaseAnonKey);
        const { data: { session } } = await sb.auth.getSession();
        return session?.access_token ?? null;
    }, []);

    // Fetch intel dashboard data for risk score breakdown (US-032)
    const fetchIntelDashboard = useCallback(async (targetSessionId: string) => {
        try {
            const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL;
            const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;

            if (!supabaseUrl || !supabaseAnonKey) return;

            const supabase = createClient(supabaseUrl, supabaseAnonKey);
            const { data: { session } } = await supabase.auth.getSession();

            if (!session?.access_token) return;

            const response = await fetch(
                `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/v1/intel/dashboard/${targetSessionId}`,
                {
                    headers: {
                        Authorization: `Bearer ${session.access_token}`,
                    },
                }
            );

            if (response.ok) {
                const data = await response.json();
                if (data.risk_score_breakdown) {
                    setRiskScoreBreakdown(data.risk_score_breakdown);
                }
                if (data.risk_score) {
                    setRiskScore(data.risk_score);
                }
            }
        } catch (err) {
            console.warn("Failed to fetch intel dashboard:", err);
        }
    }, []);

    // Auto-collapse intel side panel on narrower screens (US-026)
    useEffect(() => {
        if (!isLargeScreen) {
            setIsSidePanelCollapsed(true);
        }
    }, [isLargeScreen]);

    useEffect(() => {
        const checkAuth = async () => {
            const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL;
            const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;

            if (!supabaseUrl || !supabaseAnonKey) {
                router.push("/login");
                return;
            }

            const supabase = createClient(supabaseUrl, supabaseAnonKey);
            const { data: { user } } = await supabase.auth.getUser();

            if (!user) {
                router.push("/login");
                return;
            }

            setUser(user);
        };

        checkAuth();
    }, [router]);

    const handleAnalyze = async (contentToAnalyze: string) => {
        // Clear previous error but keep email content (US-022: session not lost on error)
        setAnalysisError(null);
        setIsRetryingAnalysis(false);

        try {
            // Reset previous result
            setClassificationResult(null);
            setShowSafeWarning(false);
            setSessionId(null);
            setMessages([]);
            setExtractedIOCs([]);
            setTimelineEvents([]);
            setRiskScoreBreakdown(undefined);
            setRiskScore(1);

            // Get auth token from Supabase
            const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL;
            const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;

            if (!supabaseUrl || !supabaseAnonKey) {
                throw new Error("Supabase configuration missing");
            }

            const supabase = createClient(supabaseUrl, supabaseAnonKey);
            const { data: { session } } = await supabase.auth.getSession();

            if (!session?.access_token) {
                throw new Error("Not authenticated");
            }

            const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/v1/classification/analyze`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${session.access_token}`,
                },
                body: JSON.stringify({ email_content: contentToAnalyze }),
            });

            if (!response.ok) {
                if (response.status === 401) {
                    throw new Error('Session expired. Please log in again.');
                }
                // Parse standardized error response (US-022)
                const errorData = await response.json().catch(() => ({}));
                throw new Error(errorData.detail || errorData.error || 'Analysis failed. Please try again.');
            }

            const data = await response.json();

            // Store session ID for response generation and URL (US-031)
            if (data.session_id) {
                setSessionId(data.session_id);
                // Store session ID in URL for persistence on refresh
                router.replace(`/dashboard?session=${data.session_id}`, { scroll: false });
            }

            // Map API response to component props
            setClassificationResult({
                attackType: data.attack_type as AttackType,
                confidence: data.confidence,
                reasoning: data.reasoning,
                persona: data.persona
            });

            // Extract IOCs from initial email classification
            if (data.extracted_iocs && data.extracted_iocs.length > 0) {
                const iocs: ExtractedIOC[] = data.extracted_iocs.map((ioc: ExtractedIOC, index: number) => ({
                    id: `initial-${index}`,
                    type: ioc.type,
                    value: ioc.value,
                    context: ioc.context,
                    is_high_value: ioc.is_high_value,
                    created_at: new Date().toISOString(),
                }));
                setExtractedIOCs(iocs);

                // Add timeline events for extracted IOCs
                const newEvents: TimelineEvent[] = iocs.map((ioc) => ({
                    id: `event-${ioc.id}`,
                    timestamp: ioc.created_at || new Date().toISOString(),
                    event_type: "ioc_extracted" as const,
                    description: `Extracted ${ioc.type.toUpperCase()}: ${ioc.value.substring(0, 20)}...`,
                    ioc_id: ioc.id,
                    is_high_value: ioc.is_high_value,
                }));
                setTimelineEvents(newEvents);
            }

            // Fetch enhanced risk score breakdown (US-032)
            if (data.session_id) {
                fetchIntelDashboard(data.session_id);
            }

            // Check if safe
            if (data.attack_type === "not_phishing") {
                setShowSafeWarning(true);
            }

        } catch (error) {
            console.error("Error analyzing email:", error);
            // Set error for display (US-022)
            setAnalysisError(error instanceof Error ? error.message : "An unexpected error occurred. Please try again.");
        }
    };

    // Retry handler for analysis errors (US-022)
    const handleRetryAnalysis = async () => {
        if (!emailContent) return;
        setIsRetryingAnalysis(true);
        await handleAnalyze(emailContent);
        setIsRetryingAnalysis(false);
    };

    const handleGenerateResponse = async () => {
        if (!sessionId) {
            console.error("No session ID available");
            return;
        }

        setIsGenerating(true);

        try {
            const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL;
            const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;

            if (!supabaseUrl || !supabaseAnonKey) {
                throw new Error("Supabase configuration missing");
            }

            const supabase = createClient(supabaseUrl, supabaseAnonKey);
            const { data: { session } } = await supabase.auth.getSession();

            if (!session?.access_token) {
                throw new Error("Not authenticated");
            }

            const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/v1/response/generate`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${session.access_token}`,
                },
                body: JSON.stringify({ session_id: sessionId }),
            });

            if (!response.ok) {
                if (response.status === 401) {
                    throw new Error('Session expired. Please log in again.');
                }
                const errorData = await response.json().catch(() => ({}));
                throw new Error(errorData.error || errorData.detail || 'Response generation failed');
            }

            const data = await response.json();

            // Add the generated response to messages
            const newMessage: ChatMessage = {
                id: data.message_id,
                sender: "bot",
                content: data.content,
                timestamp: new Date(),
                thinking: data.thinking,
            };

            setMessages(prev => [...prev, newMessage]);

            // Update turn count and limit from response (US-015)
            if (data.turn_count !== undefined) {
                setTurnCount(data.turn_count);
            }
            if (data.turn_limit !== undefined) {
                setTurnLimit(data.turn_limit);
            }
            // Show limit dialog if at limit
            if (data.is_at_limit) {
                setShowSessionLimitDialog(true);
            }

            // Track fallback model usage (US-023)
            if (data.used_fallback_model) {
                setUsedFallbackModel(true);
            }

        } catch (error) {
            console.error("Error generating response:", error);
            // Set error for display (US-022)
            setGenerationError(error instanceof Error ? error.message : "Failed to generate response. Please try again.");
        } finally {
            setIsGenerating(false);
        }
    };

    // Clear generation error when retrying
    const handleRetryGeneration = () => {
        setGenerationError(null);
        handleGenerateResponse();
    };

    const handleEditMessage = async (messageId: string, newContent: string) => {
        if (!sessionId) {
            throw new Error("No session ID available");
        }

        // Get auth token from Supabase
        const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL;
        const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;

        if (!supabaseUrl || !supabaseAnonKey) {
            throw new Error("Supabase configuration missing");
        }

        const supabase = createClient(supabaseUrl, supabaseAnonKey);
        const { data: { session } } = await supabase.auth.getSession();

        if (!session?.access_token) {
            throw new Error("Not authenticated");
        }

        // Validate the edited content through safety layer
        const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/v1/response/validate`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${session.access_token}`,
            },
            body: JSON.stringify({
                content: newContent,
                session_id: sessionId,
                message_id: messageId,
            }),
        });

        if (!response.ok) {
            if (response.status === 401) {
                throw new Error('Session expired. Please log in again.');
            }
            const errorData = await response.json().catch(() => ({}));
            throw new Error(errorData.detail || 'Validation failed');
        }

        const data = await response.json();

        if (!data.is_safe) {
            // Content failed safety validation - throw error with violations
            const violationSummary = data.violations.length > 0
                ? `Unsafe content detected: ${data.violations.join(', ')}`
                : 'Content failed safety validation';
            throw new Error(violationSummary);
        }

        // Content is safe - update the message in local state
        setMessages(prev =>
            prev.map(msg =>
                msg.id === messageId
                    ? { ...msg, content: newContent }
                    : msg
            )
        );
    };

    const handleSubmitScammerMessage = async (scammerMessage: string) => {
        if (!sessionId) {
            throw new Error("No session ID available");
        }

        setIsGenerating(true);

        try {
            const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL;
            const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;

            if (!supabaseUrl || !supabaseAnonKey) {
                throw new Error("Supabase configuration missing");
            }

            const supabase = createClient(supabaseUrl, supabaseAnonKey);
            const { data: { session } } = await supabase.auth.getSession();

            if (!session?.access_token) {
                throw new Error("Not authenticated");
            }

            const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/v1/response/generate`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${session.access_token}`,
                },
                body: JSON.stringify({
                    session_id: sessionId,
                    scammer_message: scammerMessage,
                }),
            });

            if (!response.ok) {
                if (response.status === 401) {
                    throw new Error('Session expired. Please log in again.');
                }
                const errorData = await response.json().catch(() => ({}));
                throw new Error(errorData.error || errorData.detail || 'Response generation failed');
            }

            const data = await response.json();

            // Add scammer message to local state
            const scammerChatMessage: ChatMessage = {
                id: data.scammer_message_id || `scammer-${Date.now()}`,
                sender: "scammer",
                content: scammerMessage,
                timestamp: new Date(),
            };

            // Add bot response to local state
            const botMessage: ChatMessage = {
                id: data.message_id,
                sender: "bot",
                content: data.content,
                timestamp: new Date(),
                thinking: data.thinking,
            };

            setMessages(prev => [...prev, scammerChatMessage, botMessage]);

            // Update extracted IOCs from response
            if (data.extracted_iocs && data.extracted_iocs.length > 0) {
                setExtractedIOCs(prev => [...prev, ...data.extracted_iocs]);

                // Generate timeline events for each IOC
                const newTimelineEvents: TimelineEvent[] = data.extracted_iocs.map((ioc: ExtractedIOC) => ({
                    timestamp: new Date().toISOString(),
                    event_type: "ioc_extracted" as const,
                    description: `Extracted ${ioc.type.toUpperCase()}: ${ioc.value.substring(0, 20)}...`,
                    ioc_id: ioc.id,
                    is_high_value: ioc.is_high_value,
                }));
                setTimelineEvents(prev => [...prev, ...newTimelineEvents]);

                // Refresh enhanced risk score (US-032)
                if (sessionId) {
                    fetchIntelDashboard(sessionId);
                }
            }

            // Update turn count and limit from response (US-015)
            if (data.turn_count !== undefined) {
                setTurnCount(data.turn_count);
            }
            if (data.turn_limit !== undefined) {
                setTurnLimit(data.turn_limit);
            }
            // Show limit dialog if at limit
            if (data.is_at_limit) {
                setShowSessionLimitDialog(true);
            }

            // Check for unmasking detection (US-016)
            if (data.unmasking_detected) {
                setUnmaskingPhrases(data.unmasking_phrases || []);
                setUnmaskingConfidence(data.unmasking_confidence || 0);
                setShowUnmaskingDialog(true);
            }

            // Track fallback model usage (US-023)
            if (data.used_fallback_model) {
                setUsedFallbackModel(true);
            }

        } catch (error) {
            console.error("Error submitting scammer message:", error);
            throw error; // Re-throw so ScammerInput can display the error
        } finally {
            setIsGenerating(false);
        }
    };

    const handleContinueAnyway = () => {
        setShowSafeWarning(false);
    };

    const handlePasteDifferentEmail = useCallback(() => {
        // Set flag to prevent the restore effect from re-restoring the session
        isClearingSessionRef.current = true;
        setShowSafeWarning(false);
        setClassificationResult(null);
        setEmailContent("");
        setSessionId(null);
        setMessages([]);
        setExtractedIOCs([]);
        setTimelineEvents([]);
        setRiskScoreBreakdown(undefined);
        setRiskScore(1);
        setTurnCount(0);
        setTurnLimit(20);
        setUsedFallbackModel(false);  // Reset fallback state (US-023)
        // Clear session from URL using Next.js router (US-031)
        router.replace('/dashboard', { scroll: false });
    }, [router]);

    // Handler for extending session limit (US-015)
    const handleExtendSession = async () => {
        if (!sessionId) return;

        setIsExtendingSession(true);

        try {
            const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL;
            const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;

            if (!supabaseUrl || !supabaseAnonKey) {
                throw new Error("Supabase configuration missing");
            }

            const supabase = createClient(supabaseUrl, supabaseAnonKey);
            const { data: { session } } = await supabase.auth.getSession();

            if (!session?.access_token) {
                throw new Error("Not authenticated");
            }

            const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/v1/response/session/${sessionId}/extend`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${session.access_token}`,
                },
                body: JSON.stringify({ additional_turns: 10 }),
            });

            if (!response.ok) {
                throw new Error('Failed to extend session');
            }

            const data = await response.json();
            setTurnLimit(data.new_limit);
            setShowSessionLimitDialog(false);

        } catch (error) {
            console.error("Error extending session:", error);
        } finally {
            setIsExtendingSession(false);
        }
    };

    // Handler for ending session (US-015/US-017)
    const handleEndSession = async () => {
        if (!sessionId) return;

        setIsEndingSession(true);
        setShowSessionLimitDialog(false);
        setShowUnmaskingDialog(false);

        try {
            const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL;
            const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;

            if (!supabaseUrl || !supabaseAnonKey) {
                throw new Error("Supabase configuration missing");
            }

            const supabase = createClient(supabaseUrl, supabaseAnonKey);
            const { data: { session } } = await supabase.auth.getSession();

            if (!session?.access_token) {
                throw new Error("Not authenticated");
            }

            // End the session
            const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
            console.log('Ending session:', { sessionId, apiUrl, hasToken: !!session.access_token });

            let endResponse: Response;
            try {
                endResponse = await fetch(`${apiUrl}/api/v1/session/${sessionId}/end`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'Authorization': `Bearer ${session.access_token}`,
                    },
                    body: JSON.stringify({ reason: 'manual' }),
                });
            } catch (fetchError) {
                console.error('Fetch error details:', fetchError);
                console.error('Fetch error name:', (fetchError as Error).name);
                console.error('Fetch error message:', (fetchError as Error).message);
                throw fetchError;
            }

            if (!endResponse.ok) {
                const errorText = await endResponse.text();
                console.error('End session failed:', endResponse.status, errorText);
                throw new Error(`Failed to end session: ${endResponse.status}`);
            }

            // Get the session summary
            const summaryResponse = await fetch(`${apiUrl}/api/v1/session/${sessionId}/summary`, {
                headers: {
                    'Authorization': `Bearer ${session.access_token}`,
                },
            });

            if (!summaryResponse.ok) {
                throw new Error('Failed to get session summary');
            }

            const summaryData = await summaryResponse.json();
            setSessionSummary(summaryData);
            setShowSummary(true);
            setShowEndSessionDialog(false);

        } catch (error) {
            console.error("Error ending session:", error);
            alert(`Failed to end session: ${error instanceof Error ? error.message : 'Unknown error'}`);
        } finally {
            setIsEndingSession(false);
        }
    };

    // Handler for continuing after unmasking (US-016)
    const handleUnmaskingContinue = () => {
        setShowUnmaskingDialog(false);
        setUnmaskingPhrases([]);
        setUnmaskingConfidence(0);
    };

    // Handler for exporting JSON (US-019)
    const handleExportJson = async () => {
        if (!sessionId) return;

        setIsExporting(true);
        try {
            const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL;
            const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;
            if (!supabaseUrl || !supabaseAnonKey) return;

            const supabase = createClient(supabaseUrl, supabaseAnonKey);
            const { data: { session } } = await supabase.auth.getSession();
            if (!session?.access_token) return;

            const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/v1/session/${sessionId}/export/json`, {
                headers: { 'Authorization': `Bearer ${session.access_token}` },
            });

            const blob = await response.blob();
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `phishguard_session_${new Date().toISOString().slice(0, 10)}.json`;
            a.click();
            URL.revokeObjectURL(url);
        } finally {
            setIsExporting(false);
        }
    };

    // Handler for exporting CSV (US-020)
    const handleExportCsv = async () => {
        if (!sessionId) return;

        setIsExporting(true);
        try {
            const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL;
            const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;
            if (!supabaseUrl || !supabaseAnonKey) return;

            const supabase = createClient(supabaseUrl, supabaseAnonKey);
            const { data: { session } } = await supabase.auth.getSession();
            if (!session?.access_token) return;

            const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/v1/session/${sessionId}/export/csv`, {
                headers: { 'Authorization': `Bearer ${session.access_token}` },
            });

            const blob = await response.blob();
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `phishguard_iocs_${new Date().toISOString().slice(0, 10)}.csv`;
            a.click();
            URL.revokeObjectURL(url);
        } finally {
            setIsExporting(false);
        }
    };

    // Handler for new session (US-018 & US-025)
    // Used by summary page and header button confirmation
    const handleNewSession = useCallback(() => {
        setShowSummary(false);
        setSessionSummary(null);
        handlePasteDifferentEmail();
        setShowNewSessionDialog(false);
    }, [handlePasteDifferentEmail]);

    // Restore session from URL parameter (US-031)
    const restoreSession = useCallback(async (sessionIdToRestore: string) => {
        setIsRestoringSession(true);
        try {
            const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL;
            const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;

            if (!supabaseUrl || !supabaseAnonKey) {
                throw new Error("Supabase configuration missing");
            }

            const supabase = createClient(supabaseUrl, supabaseAnonKey);
            const { data: { session } } = await supabase.auth.getSession();

            if (!session?.access_token) {
                throw new Error("Not authenticated");
            }

            const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/v1/session/${sessionIdToRestore}/restore`, {
                headers: {
                    'Authorization': `Bearer ${session.access_token}`,
                },
            });

            if (!response.ok) {
                if (response.status === 404) {
                    // Session not found, clear URL and start fresh
                    console.warn('Session not found, starting fresh');
                    window.history.replaceState(null, '', window.location.pathname);
                    return;
                }
                throw new Error('Failed to restore session');
            }

            const data = await response.json();

            // Restore session state
            setSessionId(sessionIdToRestore);
            setClassificationResult({
                attackType: data.attack_type as AttackType,
                confidence: data.confidence,
                reasoning: '', // Not stored, but not essential for restoration
                persona: data.persona,
            });

            // Restore original email content (for display purposes)
            if (data.original_email) {
                setEmailContent(data.original_email);
            }

            // Restore messages
            const restoredMessages: ChatMessage[] = data.messages.map((msg: {
                id: string;
                sender: string;
                content: string;
                timestamp: string;
                thinking?: AgentThinking;
            }) => ({
                id: msg.id,
                sender: msg.sender as "bot" | "scammer",
                content: msg.content,
                timestamp: new Date(msg.timestamp),
                thinking: msg.thinking,
            }));
            setMessages(restoredMessages);

            // Restore IOCs
            const restoredIOCs: ExtractedIOC[] = data.iocs.map((ioc: ExtractedIOC) => ({
                id: ioc.id,
                type: ioc.type,
                value: ioc.value,
                is_high_value: ioc.is_high_value,
                created_at: ioc.created_at,
            }));
            setExtractedIOCs(restoredIOCs);

            // Restore timeline events from IOCs
            const restoredEvents: TimelineEvent[] = restoredIOCs.map((ioc) => ({
                id: `event-${ioc.id}`,
                timestamp: ioc.created_at || new Date().toISOString(),
                event_type: "ioc_extracted" as const,
                description: `Extracted ${ioc.type.toUpperCase()}: ${ioc.value.substring(0, 20)}...`,
                ioc_id: ioc.id,
                is_high_value: ioc.is_high_value,
            }));
            setTimelineEvents(restoredEvents);

            // Restore turn count and limit
            setTurnCount(data.turn_count);
            setTurnLimit(data.turn_limit);

            // Fetch enhanced risk score breakdown (US-032)
            fetchIntelDashboard(sessionIdToRestore);

            console.log(`Session ${sessionIdToRestore} restored successfully`);

        } catch (error) {
            console.error('Error restoring session:', error);
            // Clear URL on error and start fresh
            window.history.replaceState(null, '', window.location.pathname);
        } finally {
            setIsRestoringSession(false);
        }
    }, [fetchIntelDashboard]);

    // Effect to restore session from URL on page load (US-031)
    useEffect(() => {
        // Skip restoration if we're intentionally clearing the session
        if (isClearingSessionRef.current) {
            // Reset the flag once the URL has been cleared
            if (!searchParams.get('session')) {
                isClearingSessionRef.current = false;
            }
            return;
        }

        const sessionParamValue = searchParams.get('session');
        if (sessionParamValue && !sessionId && user && !isRestoringSession) {
            restoreSession(sessionParamValue);
        }
    }, [searchParams, sessionId, user, isRestoringSession, restoreSession]);

    // Show loading state while restoring session (US-031)
    // Note: Auth loading is handled by AuthenticatedLayout
    if (isRestoringSession) {
        return (
            <AuthenticatedLayout onNewSession={() => setShowNewSessionDialog(true)}>
                <div className="flex min-h-screen items-center justify-center">
                    <div className="flex items-center gap-3">
                        <Loader2 className="h-6 w-6 animate-spin text-primary" />
                        <span className="text-muted-foreground">Restoring session...</span>
                    </div>
                </div>
            </AuthenticatedLayout>
        );
    }

    // Determine if we should show the chat area
    const showChatArea = classificationResult && !showSafeWarning && classificationResult.attackType !== "not_phishing";

    return (
        <AuthenticatedLayout onNewSession={() => setShowNewSessionDialog(true)}>
            <div className="flex flex-col min-h-screen">
                {/* Header */}
                <AppHeader
                    showSessionActions={!showSummary}
                    sessionId={sessionId}
                    onEndSession={() => setShowEndSessionDialog(true)}
                    onNewSession={() => setShowNewSessionDialog(true)}
                    isEndingSession={isEndingSession}
                />

                {/* New Session Confirmation Dialog (US-025) */}
                <AlertDialog open={showNewSessionDialog} onOpenChange={setShowNewSessionDialog}>
                    <AlertDialogContent data-testid="new-session-dialog">
                        <AlertDialogHeader>
                            <AlertDialogTitle>Start New Session?</AlertDialogTitle>
                            <AlertDialogDescription>
                                Are you sure you want to start a new session? Any unsaved data will be lost.
                            </AlertDialogDescription>
                        </AlertDialogHeader>
                        <AlertDialogFooter>
                            <AlertDialogCancel data-testid="new-session-cancel-button">Cancel</AlertDialogCancel>
                            <AlertDialogAction
                                onClick={handleNewSession}
                                data-testid="new-session-confirm-button"
                            >
                                Confirm
                            </AlertDialogAction>
                        </AlertDialogFooter>
                    </AlertDialogContent>
                </AlertDialog>

                {/* Main content - show summary or regular dashboard */}
                {
                    showSummary && sessionSummary ? (
                        <main className="flex flex-1 flex-col p-6">
                            <SessionSummary
                                summary={sessionSummary}
                                onExportJson={handleExportJson}
                                onExportCsv={handleExportCsv}
                                onNewSession={handleNewSession}
                                isExporting={isExporting}
                            />
                        </main>
                    ) : (
                        <main className="flex flex-1 flex-col gap-6 p-6 max-w-7xl mx-auto w-full">
                            {/* Top row: Email Input + Analysis Results */}
                            <div className="flex flex-col md:flex-row gap-6">
                                {/* Left Panel: Input */}
                                <div className={`flex-1 transition-all ${classificationResult && !showSafeWarning ? 'md:w-2/3' : 'w-full max-w-3xl mx-auto'}`}>
                                    <EmailInput
                                        value={emailContent}
                                        onChange={setEmailContent}
                                        onAnalyze={handleAnalyze}
                                    />

                                    {/* Analysis Error Display (US-022) */}
                                    {analysisError && (
                                        <div className="mt-4">
                                            <ApiError
                                                title="Analysis Failed"
                                                message={analysisError}
                                                onRetry={handleRetryAnalysis}
                                                isRetrying={isRetryingAnalysis}
                                                data-testid="analysis-error"
                                            />
                                        </div>
                                    )}
                                </div>

                                {/* Right Panel: Results (Side Panel) - Collapsible (US-026) */}
                                {classificationResult && !showSafeWarning && (
                                    <div
                                        className={`transition-all duration-300 ease-in-out ${isSidePanelCollapsed
                                            ? "w-12"
                                            : "w-full md:w-1/3"
                                            } animate-in fade-in slide-in-from-right-10`}
                                        data-testid="side-panel"
                                    >
                                        <div className="sticky top-6">
                                            {/* Collapsed state - just show toggle button */}
                                            {isSidePanelCollapsed ? (
                                                <div className="flex flex-col items-center">
                                                    <Button
                                                        variant="outline"
                                                        size="icon"
                                                        onClick={() => setIsSidePanelCollapsed(false)}
                                                        data-testid="expand-side-panel-button"
                                                        title="Expand panel"
                                                        aria-label="Expand intel panel"
                                                        className="mb-2"
                                                    >
                                                        <PanelRightOpen className="h-4 w-4" />
                                                    </Button>
                                                    {/* Show IOC count badge when collapsed */}
                                                    {extractedIOCs.length > 0 && (
                                                        <span
                                                            className="inline-flex items-center justify-center rounded-full bg-primary/10 px-2 py-1 text-xs font-medium text-primary"
                                                            title={`${extractedIOCs.length} IOCs collected`}
                                                        >
                                                            {extractedIOCs.length}
                                                        </span>
                                                    )}
                                                </div>
                                            ) : (
                                                /* Expanded state - full panel */
                                                <>
                                                    <div className="flex items-center justify-between pb-3 border-b border-border/50 mb-4">
                                                        <h3 className="text-lg font-semibold">Analysis Results</h3>
                                                        <Button
                                                            variant="ghost"
                                                            size="icon"
                                                            onClick={() => setIsSidePanelCollapsed(true)}
                                                            data-testid="collapse-side-panel-button"
                                                            title="Collapse panel"
                                                            aria-label="Collapse intel panel"
                                                        >
                                                            <PanelRightClose className="h-4 w-4" />
                                                        </Button>
                                                    </div>
                                                    <div className="space-y-4">
                                                        <ClassificationResult
                                                            attackType={classificationResult.attackType}
                                                            confidence={classificationResult.confidence}
                                                            reasoning={classificationResult.reasoning}
                                                        />
                                                        {classificationResult.persona && (
                                                            <PersonaCard persona={classificationResult.persona} />
                                                        )}
                                                        <IntelDashboard
                                                            iocs={extractedIOCs}
                                                            attackType={classificationResult.attackType}
                                                            confidence={classificationResult.confidence}
                                                            riskScore={riskScore || Math.min(10, Math.max(1,
                                                                (classificationResult.attackType === 'ceo_fraud' || classificationResult.attackType === 'crypto_investment' ? 4 :
                                                                    classificationResult.attackType === 'not_phishing' ? 1 : 3) +
                                                                Math.min(extractedIOCs.length, 3) +
                                                                Math.min(extractedIOCs.filter(ioc => ioc.is_high_value).length, 3)
                                                            ))}
                                                            riskScoreBreakdown={riskScoreBreakdown}
                                                            timeline={timelineEvents}
                                                            getAccessToken={getAccessToken}
                                                            onEnrichmentComplete={() => { if (sessionId) fetchIntelDashboard(sessionId); }}
                                                        />
                                                    </div>
                                                </>
                                            )}
                                        </div>
                                    </div>
                                )}
                            </div>

                            {/* Chat Area - shown after classification */}
                            {showChatArea && (
                                <div className="animate-in fade-in slide-in-from-bottom-10 duration-500">
                                    <ChatArea
                                        messages={messages}
                                        isGenerating={isGenerating}
                                        onGenerateResponse={handleGenerateResponse}
                                        showGenerateButton={sessionId !== null}
                                        onEditMessage={handleEditMessage}
                                        onSubmitScammerMessage={handleSubmitScammerMessage}
                                        sessionId={sessionId ?? undefined}
                                        turnCount={turnCount}
                                        turnLimit={turnLimit}
                                        usedFallbackModel={usedFallbackModel}
                                    />

                                    {/* Generation Error Display (US-022) */}
                                    {generationError && (
                                        <div className="mt-4">
                                            <ApiError
                                                title="Response Generation Failed"
                                                message={generationError}
                                                onRetry={handleRetryGeneration}
                                                isRetrying={isGenerating}
                                                data-testid="generation-error"
                                            />
                                        </div>
                                    )}
                                </div>
                            )}
                        </main>
                    )
                }

                {/* Session Limit Dialog (US-015) */}
                <SessionLimitDialog
                    open={showSessionLimitDialog}
                    turnCount={turnCount}
                    turnLimit={turnLimit}
                    onContinue={handleExtendSession}
                    onEndSession={handleEndSession}
                    isExtending={isExtendingSession}
                />

                <AlertDialog open={showSafeWarning} onOpenChange={setShowSafeWarning}>
                    <AlertDialogContent>
                        <AlertDialogHeader>
                            <AlertDialogTitle>Possible Safe Email Detected</AlertDialogTitle>
                            <AlertDialogDescription>
                                This email doesn&apos;t appear to be phishing (Confidence: {classificationResult?.confidence}%).
                                PhishGuard is designed to simulate conversations with scammers.
                                Are you sure you want to continue with a legitimate email?
                            </AlertDialogDescription>
                        </AlertDialogHeader>
                        <AlertDialogFooter>
                            <AlertDialogCancel onClick={handlePasteDifferentEmail}>Paste different email</AlertDialogCancel>
                            <AlertDialogAction onClick={handleContinueAnyway}>Continue anyway</AlertDialogAction>
                        </AlertDialogFooter>
                    </AlertDialogContent>
                </AlertDialog>

                {/* Unmasking Dialog (US-016) */}
                <UnmaskingDialog
                    open={showUnmaskingDialog}
                    matchedPhrases={unmaskingPhrases}
                    confidence={unmaskingConfidence}
                    onSummarize={handleEndSession}
                    onContinue={handleUnmaskingContinue}
                    isLoading={isEndingSession}
                />

                {/* End Session Confirmation Dialog (US-017) */}
                <EndSessionDialog
                    open={showEndSessionDialog}
                    onOpenChange={setShowEndSessionDialog}
                    onConfirm={handleEndSession}
                    isLoading={isEndingSession}
                />
            </div>
        </AuthenticatedLayout>
    );
}
