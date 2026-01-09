"use client";

import { useEffect, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { createClient, User } from "@supabase/supabase-js";
import { Loader2 } from "lucide-react";
import { AppHeader } from "@/components/app/AppHeader";
import { EmptyState } from "@/components/history/EmptyState";
import { SessionHistoryList } from "@/components/history/SessionHistoryList";
import { Pagination } from "@/components/history/Pagination";
import { ApiError } from "@/components/app/ApiError";
import { PaginatedSessionsResponse, SessionHistoryItem } from "@/types/schemas";

const SESSIONS_PER_PAGE = 20;

export default function HistoryPage() {
    const router = useRouter();
    const [user, setUser] = useState<User | null>(null);
    const [isLoading, setIsLoading] = useState(true);
    const [isSigningOut, setIsSigningOut] = useState(false);
    const [sessions, setSessions] = useState<SessionHistoryItem[]>([]);
    const [currentPage, setCurrentPage] = useState(1);
    const [totalPages, setTotalPages] = useState(0);
    const [error, setError] = useState<string | null>(null);
    const [isRetrying, setIsRetrying] = useState(false);
    const [isFetchingSessions, setIsFetchingSessions] = useState(false);

    // Fetch sessions from API
    const fetchSessions = useCallback(async (page: number, accessToken: string) => {
        setIsFetchingSessions(true);
        setError(null);

        try {
            const response = await fetch(
                `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/v1/sessions?page=${page}&per_page=${SESSIONS_PER_PAGE}`,
                {
                    headers: {
                        Authorization: `Bearer ${accessToken}`,
                    },
                }
            );

            if (!response.ok) {
                if (response.status === 401) {
                    router.push("/login");
                    return;
                }
                const errorData = await response.json().catch(() => ({}));
                throw new Error(errorData.error || "Failed to fetch sessions");
            }

            const data: PaginatedSessionsResponse = await response.json();
            setSessions(data.items);
            setTotalPages(data.total_pages);
            setCurrentPage(data.page);
        } catch (err) {
            console.error("Error fetching sessions:", err);
            setError(err instanceof Error ? err.message : "Failed to load session history");
        } finally {
            setIsFetchingSessions(false);
        }
    }, [router]);

    // Auth check and initial fetch
    useEffect(() => {
        const checkAuthAndFetch = async () => {
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

            // Get access token for API calls
            const { data: { session } } = await supabase.auth.getSession();
            if (session?.access_token) {
                await fetchSessions(1, session.access_token);
            }

            setIsLoading(false);
        };

        checkAuthAndFetch();
    }, [router, fetchSessions]);

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

    const handlePageChange = async (page: number) => {
        const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL;
        const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;

        if (!supabaseUrl || !supabaseAnonKey) return;

        const supabase = createClient(supabaseUrl, supabaseAnonKey);
        const { data: { session } } = await supabase.auth.getSession();

        if (session?.access_token) {
            await fetchSessions(page, session.access_token);
        }
    };

    const handleRetry = async () => {
        setIsRetrying(true);

        const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL;
        const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;

        if (!supabaseUrl || !supabaseAnonKey) {
            setIsRetrying(false);
            return;
        }

        const supabase = createClient(supabaseUrl, supabaseAnonKey);
        const { data: { session } } = await supabase.auth.getSession();

        if (session?.access_token) {
            await fetchSessions(currentPage, session.access_token);
        }

        setIsRetrying(false);
    };

    const handleSessionClick = (sessionId: string) => {
        // Navigate to session detail view (US-029)
        router.push(`/history/${sessionId}`);
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

    if (!user) {
        return null;
    }

    return (
        <div className="flex min-h-screen flex-col bg-background">
            <AppHeader
                user={user}
                onSignOut={handleSignOut}
                isSigningOut={isSigningOut}
            />

            <main className="flex flex-1 flex-col p-6">
                <div className="max-w-4xl mx-auto w-full">
                    <div className="mb-6">
                        <h1 className="text-2xl font-bold tracking-tight">Session History</h1>
                        <p className="text-sm text-muted-foreground mt-1">
                            View and manage your previous phishing analysis sessions
                        </p>
                    </div>

                    {/* Error state */}
                    {error && (
                        <div className="mb-6">
                            <ApiError
                                title="Failed to Load Sessions"
                                message={error}
                                onRetry={handleRetry}
                                isRetrying={isRetrying}
                            />
                        </div>
                    )}

                    {/* Loading state for page changes */}
                    {isFetchingSessions && !error && (
                        <div className="flex items-center justify-center py-12">
                            <div className="flex items-center gap-3">
                                <Loader2 className="h-6 w-6 animate-spin text-primary" />
                                <span className="text-muted-foreground">Loading sessions...</span>
                            </div>
                        </div>
                    )}

                    {/* Empty state */}
                    {!isFetchingSessions && !error && sessions.length === 0 && (
                        <div className="py-12">
                            <EmptyState />
                        </div>
                    )}

                    {/* Session list */}
                    {!isFetchingSessions && !error && sessions.length > 0 && (
                        <>
                            <SessionHistoryList
                                sessions={sessions}
                                onSessionClick={handleSessionClick}
                            />

                            {/* Pagination */}
                            {totalPages > 1 && (
                                <div className="mt-6">
                                    <Pagination
                                        currentPage={currentPage}
                                        totalPages={totalPages}
                                        onPageChange={handlePageChange}
                                    />
                                </div>
                            )}
                        </>
                    )}
                </div>
            </main>
        </div>
    );
}
