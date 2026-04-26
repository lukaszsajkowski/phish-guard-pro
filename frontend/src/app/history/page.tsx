"use client";

import { useEffect, useState, useCallback, type FormEvent } from "react";
import { useRouter } from "next/navigation";
import { createClient } from "@supabase/supabase-js";
import { Filter, Search, X } from "lucide-react";
import { AuthenticatedLayout } from "@/components/app/AuthenticatedLayout";
import { HistoryListSkeleton } from "@/components/app/LoadingSkeletons";
import { EmptyState } from "@/components/history/EmptyState";
import { SessionHistoryList } from "@/components/history/SessionHistoryList";
import { Pagination } from "@/components/history/Pagination";
import { ApiError } from "@/components/app/ApiError";
import { PaginatedSessionsResponse, SessionHistoryItem } from "@/types/schemas";
import { ATTACK_TYPE_LABELS } from "@/lib/constants/ioc";

const SESSIONS_PER_PAGE = 20;
const RISK_FILTERS = [
    { label: "All risks", value: "" },
    { label: "High (7+)", value: "7" },
    { label: "Medium+ (4+)", value: "4" },
];

export default function HistoryPage() {
    const router = useRouter();
    const [sessions, setSessions] = useState<SessionHistoryItem[]>([]);
    const [currentPage, setCurrentPage] = useState(1);
    const [totalPages, setTotalPages] = useState(0);
    const [error, setError] = useState<string | null>(null);
    const [isRetrying, setIsRetrying] = useState(false);
    const [isFetchingSessions, setIsFetchingSessions] = useState(true);
    const [searchInput, setSearchInput] = useState("");
    const [searchTerm, setSearchTerm] = useState("");
    const [attackTypeFilter, setAttackTypeFilter] = useState("");
    const [minRiskFilter, setMinRiskFilter] = useState("");

    const hasActiveFilters = Boolean(searchTerm || attackTypeFilter || minRiskFilter);

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

            const params = new URLSearchParams({
                page: String(page),
                per_page: String(SESSIONS_PER_PAGE),
            });
            if (searchTerm) params.set("search", searchTerm);
            if (attackTypeFilter) params.set("attack_type", attackTypeFilter);
            if (minRiskFilter) params.set("min_risk", minRiskFilter);

            const response = await fetch(
                `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/v1/sessions?${params.toString()}`,
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
    }, [router, searchTerm, attackTypeFilter, minRiskFilter]);

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

    const handleSearchSubmit = async (event: FormEvent<HTMLFormElement>) => {
        event.preventDefault();
        setSearchTerm(searchInput.trim());
    };

    const clearFilters = () => {
        setSearchInput("");
        setSearchTerm("");
        setAttackTypeFilter("");
        setMinRiskFilter("");
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

                    <div className="mb-6 rounded-lg border border-border bg-card p-4">
                        <form
                            onSubmit={handleSearchSubmit}
                            className="grid gap-3 lg:grid-cols-[1fr_180px_150px_auto]"
                        >
                            <label className="relative block">
                                <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                                <input
                                    type="search"
                                    value={searchInput}
                                    onChange={(event) => setSearchInput(event.target.value)}
                                    placeholder="Search title or attack type"
                                    className="h-10 w-full rounded-md border border-input bg-background pl-9 pr-3 text-sm outline-none transition-colors focus:border-primary"
                                    data-testid="history-search-input"
                                />
                            </label>

                            <label className="relative block">
                                <Filter className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                                <select
                                    value={attackTypeFilter}
                                    onChange={(event) => setAttackTypeFilter(event.target.value)}
                                    className="h-10 w-full rounded-md border border-input bg-background pl-9 pr-3 text-sm outline-none transition-colors focus:border-primary"
                                    data-testid="history-attack-filter"
                                >
                                    <option value="">All attack types</option>
                                    {Object.entries(ATTACK_TYPE_LABELS).map(([value, label]) => (
                                        <option key={value} value={value}>
                                            {label}
                                        </option>
                                    ))}
                                </select>
                            </label>

                            <select
                                value={minRiskFilter}
                                onChange={(event) => setMinRiskFilter(event.target.value)}
                                className="h-10 w-full rounded-md border border-input bg-background px-3 text-sm outline-none transition-colors focus:border-primary"
                                data-testid="history-risk-filter"
                            >
                                {RISK_FILTERS.map((filter) => (
                                    <option key={filter.value || "all"} value={filter.value}>
                                        {filter.label}
                                    </option>
                                ))}
                            </select>

                            <div className="flex gap-2">
                                <button
                                    type="submit"
                                    className="inline-flex h-10 items-center justify-center gap-2 rounded-md bg-primary px-4 text-sm font-medium text-primary-foreground transition-colors hover:bg-primary/90"
                                >
                                    <Search className="h-4 w-4" />
                                    Search
                                </button>
                                {hasActiveFilters && (
                                    <button
                                        type="button"
                                        onClick={clearFilters}
                                        className="inline-flex h-10 w-10 items-center justify-center rounded-md border border-input text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
                                        aria-label="Clear filters"
                                        title="Clear filters"
                                        data-testid="history-clear-filters"
                                    >
                                        <X className="h-4 w-4" />
                                    </button>
                                )}
                            </div>
                        </form>
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
                    {!isFetchingSessions && !error && sessions.length === 0 && !hasActiveFilters && (
                        <div className="py-12">
                            <EmptyState />
                        </div>
                    )}

                    {!isFetchingSessions && !error && sessions.length === 0 && hasActiveFilters && (
                        <div className="rounded-lg border border-border bg-card p-8 text-center">
                            <h2 className="text-sm font-semibold">No matching sessions</h2>
                            <p className="mt-1 text-sm text-muted-foreground">
                                Adjust the search or filters to broaden the result set.
                            </p>
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
