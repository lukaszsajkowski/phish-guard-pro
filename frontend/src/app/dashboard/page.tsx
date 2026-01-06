"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Shield, LogOut, Loader2 } from "lucide-react";
import Link from "next/link";
import { createClient, User } from "@supabase/supabase-js";
import { EmailInput } from "@/components/app/email-input";
import { ClassificationResult } from "@/components/app/ClassificationResult";
import { PersonaCard } from "@/components/dashboard/PersonaCard";
import { ChatArea } from "@/components/dashboard/ChatArea";
import { IntelDashboard } from "@/components/dashboard/IntelDashboard";
import { SessionLimitDialog } from "@/components/dashboard/SessionLimitDialog";
import { Persona, ChatMessage, ExtractedIOC, TimelineEvent } from "@/types/schemas";

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

export default function DashboardPage() {
    const router = useRouter();
    const [user, setUser] = useState<User | null>(null);
    const [isLoading, setIsLoading] = useState(true);
    const [isSigningOut, setIsSigningOut] = useState(false);
    const [emailContent, setEmailContent] = useState("");
    const [showSafeWarning, setShowSafeWarning] = useState(false);
    const [sessionId, setSessionId] = useState<string | null>(null);
    const [isGenerating, setIsGenerating] = useState(false);
    const [messages, setMessages] = useState<ChatMessage[]>([]);
    const [classificationResult, setClassificationResult] = useState<{
        attackType: any;
        confidence: number;
        reasoning: string;
        persona?: Persona;
    } | null>(null);
    const [extractedIOCs, setExtractedIOCs] = useState<ExtractedIOC[]>([]);
    const [timelineEvents, setTimelineEvents] = useState<TimelineEvent[]>([]);
    // Turn count and limit state (US-015)
    const [turnCount, setTurnCount] = useState(0);
    const [turnLimit, setTurnLimit] = useState(20);
    const [showSessionLimitDialog, setShowSessionLimitDialog] = useState(false);
    const [isExtendingSession, setIsExtendingSession] = useState(false);

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
            setIsLoading(false);
        };

        checkAuth();
    }, [router]);

    const handleSignOut = async () => {
        setIsSigningOut(true);

        try {
            const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL;
            const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;

            if (!supabaseUrl || !supabaseAnonKey) {
                throw new Error("Supabase configuration missing");
            }

            const supabase = createClient(supabaseUrl, supabaseAnonKey);
            await supabase.auth.signOut();
            router.push("/login");
        } catch {
            setIsSigningOut(false);
        }
    };

    const handleAnalyze = async (contentToAnalyze: string) => {
        try {
            // Reset previous result
            setClassificationResult(null);
            setShowSafeWarning(false);
            setSessionId(null);
            setMessages([]);
            setExtractedIOCs([]);
            setTimelineEvents([]);

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
                throw new Error('Analysis failed');
            }

            const data = await response.json();

            // Store session ID for response generation
            if (data.session_id) {
                setSessionId(data.session_id);
            }

            // Map API response to component props
            setClassificationResult({
                attackType: data.attack_type,
                confidence: data.confidence,
                reasoning: data.reasoning,
                persona: data.persona
            });

            // Check if safe
            if (data.attack_type === "not_phishing") {
                setShowSafeWarning(true);
            }

        } catch (error) {
            console.error("Error analyzing email:", error);
            // TODO: generic error handling UI
        }
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
                throw new Error(errorData.detail || 'Response generation failed');
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

        } catch (error) {
            console.error("Error generating response:", error);
            // TODO: Show error toast
        } finally {
            setIsGenerating(false);
        }
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
                throw new Error(errorData.detail || 'Response generation failed');
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

    const handlePasteDifferentEmail = () => {
        setShowSafeWarning(false);
        setClassificationResult(null);
        setEmailContent("");
        setSessionId(null);
        setMessages([]);
        setExtractedIOCs([]);
        setTimelineEvents([]);
        setTurnCount(0);
        setTurnLimit(20);
    };

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

    // Handler for ending session (US-015)
    const handleEndSession = () => {
        // TODO: Implement session summary page/modal (US-018)
        setShowSessionLimitDialog(false);
        // For now, just close the dialog - summary feature to be implemented later
    };

    if (isLoading) {
        return (
            <div className="flex min-h-screen items-center justify-center bg-background">
                <div className="flex items-center gap-3">
                    <Loader2 className="h-6 w-6 animate-spin text-primary" />
                    <span className="text-muted-foreground">Loading...</span>
                </div>
            </div>
        );
    }

    // Determine if we should show the chat area
    const showChatArea = classificationResult && !showSafeWarning && classificationResult.attackType !== "not_phishing";

    return (
        <div className="flex min-h-screen flex-col bg-background">
            {/* Header */}
            <header className="border-b border-border/40 bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
                <div className="container flex h-16 items-center justify-between px-4">
                    <Link href="/dashboard" className="flex items-center gap-2">
                        <Shield className="h-8 w-8 text-primary" />
                        <span className="text-xl font-bold tracking-tight">
                            PhishGuard Pro
                        </span>
                    </Link>
                    <div className="flex items-center gap-4">
                        <span className="text-sm text-muted-foreground">
                            {user?.email}
                        </span>
                        <button
                            id="signout-button"
                            onClick={handleSignOut}
                            disabled={isSigningOut}
                            className="inline-flex items-center gap-2 rounded-md border border-border bg-background px-4 py-2 text-sm font-medium transition-colors hover:bg-muted disabled:pointer-events-none disabled:opacity-50"
                        >
                            {isSigningOut ? (
                                <>
                                    <Loader2 className="h-4 w-4 animate-spin" />
                                    Signing out...
                                </>
                            ) : (
                                <>
                                    <LogOut className="h-4 w-4" />
                                    Sign out
                                </>
                            )}
                        </button>
                    </div>
                </div>
            </header>

            {/* Main content */}
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
                    </div>

                    {/* Right Panel: Results (Side Panel) */}
                    {classificationResult && !showSafeWarning && (
                        <div className="w-full md:w-1/3 animate-in fade-in slide-in-from-right-10 duration-500">
                            <div className="sticky top-6 space-y-4">
                                <h3 className="text-lg font-semibold text-foreground/80">Analysis Results</h3>
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
                                    riskScore={Math.min(10, Math.max(1,
                                        (classificationResult.attackType === 'ceo_fraud' || classificationResult.attackType === 'crypto_investment' ? 4 :
                                            classificationResult.attackType === 'not_phishing' ? 1 : 3) +
                                        Math.min(extractedIOCs.length, 3) +
                                        Math.min(extractedIOCs.filter(ioc => ioc.is_high_value).length, 3)
                                    ))}
                                    timeline={timelineEvents}
                                />
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
                        />
                    </div>
                )}
            </main>

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
                            This email doesn't appear to be phishing (Confidence: {classificationResult?.confidence}%).
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
        </div>
    );
}
