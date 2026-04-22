"use client";

import { useEffect, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { createClient } from "@supabase/supabase-js";
import { AuthenticatedLayout } from "@/components/app/AuthenticatedLayout";
import { HistoryListSkeleton } from "@/components/app/LoadingSkeletons";
import { EmptyState } from "@/components/history/EmptyState";
import { SessionHistoryList } from "@/components/history/SessionHistoryList";
import { Pagination } from "@/components/history/Pagination";
import { ApiError } from "@/components/app/ApiError";
import { PaginatedSessionsResponse, SessionHistoryItem } from "@/types/schemas";

const SESSIONS_PER_PAGE = 20;

export default function HistoryPage() {
    const router = useRouter();
    const [sessions, setSessions] = useState<SessionHistoryItem[]>([]);
    const [currentPage, setCurrentPage] = useState(1);
    const [totalPages, setTotalPages] = useState(0);
    const [error, setError] = useState<string | null>(null);
    const [isRetrying, setIsRetrying] = useState(false);
    const [isFetchingSessions, setIsFetchingSessions] = useState(true);

    // Fetch sessions from API
    const fetchSessions = useCallback(async (page: number) => {
        setIsFetchingSessions(true);
        setError(null);

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
                `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/v1/sessions?page=${page}&per_page=${SESSIONS_PER_PAGE}`,
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

    // Initial fetch
    useEffect(() => {
        fetchSessions(1);
    }, [fetchSessions]);

    const handlePageChange = async (page: number) => {
        await fetchSessions(page);
    };

    const handleRetry = async () => {
        setIsRetrying(true);
        await fetchSessions(currentPage);
        setIsRetrying(false);
    };

    const handleSessionClick = (sessionId: string) => {
        router.push(`/history/${sessionId}`);
    };

    const handleNewSession = () => {
        router.push("/dashboard");
    };

    return (
        <AuthenticatedLayout onNewSession={handleNewSession}>
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
                        <HistoryListSkeleton />
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
        </AuthenticatedLayout>
    );
}
