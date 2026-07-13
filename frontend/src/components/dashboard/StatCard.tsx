"use client";

import { cn } from "@/lib/utils";
import { LucideIcon } from "lucide-react";
import {
    Tooltip,
    TooltipContent,
    TooltipTrigger,
} from "@/components/ui/tooltip";

interface StatCardProps {
    icon: LucideIcon;
    label: string;
    children: React.ReactNode;
    testId?: string;
    valueClassName?: string;
    tooltip?: string;
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
    tooltip,
}: StatCardProps) {
    const CardContent = (
        <div className="p-4 rounded-lg bg-muted/30 border border-border/50 transition-colors hover:bg-muted/50 cursor-default">
            <div className="flex items-center gap-2 mb-2">
                <Icon className="w-4 h-4 text-muted-foreground" />
                <span className="text-sm text-muted-foreground">{label}</span>
            </div>
            <p
                className={cn("text-2xl font-bold font-mono", valueClassName)}
                data-testid={testId}
            >
                {children}
            </p>
        </div>
    );

    if (tooltip) {
        return (
            <Tooltip delayDuration={300}>
                <TooltipTrigger asChild>
                    {CardContent}
                </TooltipTrigger>
                <TooltipContent>
                    <p>{tooltip}</p>
                </TooltipContent>
            </Tooltip>
        );
    }

    return CardContent;
}
