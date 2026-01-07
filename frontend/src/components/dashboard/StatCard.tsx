"use client";

import { cn } from "@/lib/utils";
import { LucideIcon } from "lucide-react";

interface StatCardProps {
    icon: LucideIcon;
    label: string;
    children: React.ReactNode;
    testId?: string;
    valueClassName?: string;
}

/**
 * StatCard - Reusable stat display card for dashboards
 *
 * Used in SessionSummary for displaying metrics like:
 * - Exchange count
 * - Duration
 * - IOCs found
 * - Risk score
 */
export function StatCard({
    icon: Icon,
    label,
    children,
    testId,
    valueClassName,
}: StatCardProps) {
    return (
        <div className="p-4 rounded-lg bg-muted/30 border border-border/50">
            <div className="flex items-center gap-2 mb-2">
                <Icon className="w-4 h-4 text-muted-foreground" />
                <span className="text-sm text-muted-foreground">{label}</span>
            </div>
            <p
                className={cn("text-2xl font-bold", valueClassName)}
                data-testid={testId}
            >
                {children}
            </p>
        </div>
    );
}
