"use client";

import { Skeleton } from "@/components/ui/skeleton";

export function HistoryListSkeleton() {
    return (
        <div className="max-w-4xl mx-auto w-full">
            {/* Page title */}
            <div className="mb-6">
                <Skeleton className="h-7 w-48" />
                <Skeleton className="h-4 w-72 mt-2" />
            </div>

            {/* Session cards */}
            <div className="space-y-3">
                {Array.from({ length: 5 }).map((_, i) => (
                    <div
                        key={i}
                        className="flex items-center justify-between rounded-lg border border-border p-4"
                    >
                        <div className="flex flex-col gap-2">
                            <Skeleton className="h-5 w-24 rounded-full" />
                            <div className="flex items-center gap-3">
                                <Skeleton className="h-4 w-20" />
                                <Skeleton className="h-4 w-20" />
                                <Skeleton className="h-4 w-20" />
                            </div>
                        </div>
                        <Skeleton className="h-5 w-28" />
                    </div>
                ))}
            </div>
        </div>
    );
}

export function SessionDetailSkeleton() {
    return (
        <div className="flex flex-col h-screen overflow-hidden">
            {/* Header bar */}
            <div className="flex items-center justify-between h-14 px-4 border-b border-border">
                <div className="flex items-center gap-4">
                    <Skeleton className="h-4 w-24" />
                    <div className="flex items-center gap-2">
                        <Skeleton className="h-5 w-20 rounded-full" />
                        <Skeleton className="h-5 w-16 rounded-full" />
                        <Skeleton className="h-5 w-24 rounded-full" />
                    </div>
                </div>
                <div className="flex items-center gap-2">
                    <Skeleton className="h-9 w-24 rounded-md" />
                    <Skeleton className="h-9 w-24 rounded-md" />
                </div>
            </div>

            {/* Content area */}
            <div className="flex flex-1 overflow-hidden">
                {/* Left column */}
                <div className="flex-1 px-7 py-6 flex flex-col gap-5 min-w-0">
                    {/* Persona card skeleton */}
                    <Skeleton className="h-28 w-full rounded-lg" />

                    {/* Email card skeleton */}
                    <Skeleton className="h-40 w-full rounded-lg" />

                    {/* Chat bubble skeletons */}
                    <div className="flex flex-col gap-4">
                        <div className="flex justify-start">
                            <Skeleton className="h-16 w-3/4 rounded-lg" />
                        </div>
                        <div className="flex justify-end">
                            <Skeleton className="h-16 w-2/3 rounded-lg" />
                        </div>
                        <div className="flex justify-start">
                            <Skeleton className="h-16 w-3/4 rounded-lg" />
                        </div>
                    </div>
                </div>

                {/* Right column — intel panel */}
                <aside className="w-[320px] shrink-0 border-l border-border p-4 hidden lg:block">
                    <div className="flex flex-col gap-4">
                        {/* Attack type */}
                        <Skeleton className="h-16 w-full rounded-lg" />
                        {/* IOC list */}
                        <Skeleton className="h-32 w-full rounded-lg" />
                        {/* Risk score */}
                        <Skeleton className="h-20 w-full rounded-lg" />
                        {/* Timeline */}
                        <Skeleton className="h-24 w-full rounded-lg" />
                    </div>
                </aside>
            </div>
        </div>
    );
}

export function DashboardSkeleton() {
    return (
        <div className="flex min-h-screen flex-col bg-background">
            {/* Header bar */}
            <Skeleton className="h-14 w-full" />

            {/* Centered card */}
            <div className="flex flex-1 items-center justify-center p-6">
                <div className="flex flex-col items-center gap-4 w-full max-w-3xl">
                    <Skeleton className="h-16 w-16 rounded-full" />
                    <Skeleton className="h-7 w-64" />
                    <Skeleton className="h-4 w-80" />
                    <Skeleton className="h-[300px] w-full rounded-md" />
                    <Skeleton className="h-12 w-full rounded-md" />
                </div>
            </div>
        </div>
    );
}
