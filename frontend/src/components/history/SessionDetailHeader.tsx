"use client";

import Link from "next/link";
import { FileJson, FileSpreadsheet, Download, ChevronDown } from "lucide-react";
import { format } from "date-fns";
import { cn } from "@/lib/utils";
import {
    DropdownMenu,
    DropdownMenuContent,
    DropdownMenuItem,
    DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";

interface SessionDetailHeaderProps {
    attackType: string;
    attackTypeDisplay: string;
    createdAt: string;
    status: string;
    turnCount: number;
    onExportJson?: () => void;
    onExportCsv?: () => void;
    onExportSession?: () => void;
    isExporting?: boolean;
}

function formatCreatedAt(dateString: string): string {
    try {
        const date = new Date(dateString);
        return format(date, "PPp"); // e.g., "Jan 9, 2026, 2:30 PM"
    } catch {
        return "Unknown date";
    }
}

function formatStatus(status: string): string {
    return status.charAt(0).toUpperCase() + status.slice(1);
}

export function SessionDetailHeader({
    attackTypeDisplay,
    createdAt,
    status,
    turnCount,
    onExportJson,
    onExportCsv,
    onExportSession,
    isExporting,
}: SessionDetailHeaderProps) {
    const isActive = status === "active";

    return (
        <div
            className="flex items-center justify-between gap-4 px-7 py-3.5 border-b border-border bg-surface shrink-0"
            data-testid="session-detail-header"
        >
            {/* Left side */}
            <div className="flex flex-col gap-2">
                {/* Back link */}
                <Link
                    href="/history"
                    className="inline-flex items-center gap-1.5 text-[12.5px] text-text-muted hover:text-text-secondary transition-colors w-fit"
                    data-testid="back-to-history-link"
                >
                    <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" className="w-[13px] h-[13px]">
                        <path d="M10 4L6 8l4 4" />
                    </svg>
                    Back to history
                </Link>

                {/* Session metadata row */}
                <div className="flex items-center gap-2.5 flex-wrap">
                    {/* Attack type pill */}
                    <span
                        className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[11.5px] font-medium tracking-[0.01em] bg-pg-accent-dim text-pg-accent border border-pg-accent"
                        data-testid="attack-type-badge"
                    >
                        {attackTypeDisplay}
                    </span>

                    {/* Status badge with dot */}
                    <span
                        className={cn(
                            "inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[11.5px] font-medium tracking-[0.01em] border",
                            isActive
                                ? "bg-pg-green-dim text-pg-green border-pg-green"
                                : "bg-pg-blue-dim text-pg-blue border-pg-blue"
                        )}
                        data-testid="status-badge"
                    >
                        <span
                            className={cn(
                                "w-[5px] h-[5px] rounded-full",
                                isActive ? "bg-pg-green" : "bg-pg-blue"
                            )}
                        />
                        {formatStatus(status)}
                    </span>

                    <span className="text-border2">·</span>

                    {/* Date */}
                    <span className="flex items-center gap-1.5 text-[12.5px] text-text-muted">
                        <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" className="w-[13px] h-[13px]">
                            <path d="M3 6h10M5 3v2M11 3v2M3 5a1 1 0 0 1 1-1h8a1 1 0 0 1 1 1v7a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1V5z" />
                        </svg>
                        <span data-testid="created-at">{formatCreatedAt(createdAt)}</span>
                    </span>

                    <span className="text-border2">·</span>

                    {/* Turn count */}
                    <span className="flex items-center gap-1.5 text-[12.5px] text-text-muted">
                        <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" className="w-[13px] h-[13px]">
                            <path d="M3 5h10v7a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1V5z" />
                            <path d="M6 5V3.5C6 3.2 6.2 3 6.5 3h3c.3 0 .5.2.5.5V5" />
                        </svg>
                        <span data-testid="turn-count">
                            {turnCount} {turnCount === 1 ? "turn" : "turns"}
                        </span>
                    </span>
                </div>
            </div>

            {/* Right side — action buttons */}
            <div className="flex items-center gap-2">
                {/* Export Session */}
                <button
                    className="flex items-center gap-1.5 px-3.5 py-[7px] rounded-[5px] text-[12.5px] font-medium border border-border2 text-text-secondary bg-transparent hover:bg-surface2 hover:text-text transition-all cursor-pointer"
                    onClick={onExportSession || onExportJson}
                    disabled={isExporting}
                    data-testid="export-session-button"
                >
                    <Download className="w-[13px] h-[13px]" />
                    Export Session
                </button>

                {/* Export Data dropdown — shadcn/ui for full keyboard accessibility */}
                <DropdownMenu>
                    <DropdownMenuTrigger asChild>
                        <button
                            className="flex items-center gap-1.5 px-3.5 py-[7px] rounded-[5px] text-[12.5px] font-medium border border-border2 text-text-secondary bg-transparent hover:bg-surface2 hover:text-text transition-all cursor-pointer"
                            disabled={isExporting}
                            data-testid="export-data-button"
                        >
                            <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" className="w-[13px] h-[13px]">
                                <path d="M4 8h8M4 4h8M4 12h4" />
                            </svg>
                            Export Data
                            <ChevronDown className="w-[11px] h-[11px]" />
                        </button>
                    </DropdownMenuTrigger>
                    <DropdownMenuContent align="end">
                        <DropdownMenuItem
                            onClick={() => onExportJson?.()}
                            data-testid="export-json-button"
                        >
                            <FileJson className="w-4 h-4 mr-2" />
                            Export JSON
                        </DropdownMenuItem>
                        <DropdownMenuItem
                            onClick={() => onExportCsv?.()}
                            data-testid="export-csv-button"
                        >
                            <FileSpreadsheet className="w-4 h-4 mr-2" />
                            Export CSV
                        </DropdownMenuItem>
                    </DropdownMenuContent>
                </DropdownMenu>
            </div>
        </div>
    );
}
