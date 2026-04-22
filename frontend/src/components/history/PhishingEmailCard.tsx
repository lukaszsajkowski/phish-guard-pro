"use client";

import { useState } from "react";

interface PhishingEmailCardProps {
    emailContent: string;
    subject?: string;
    from?: string;
    to?: string;
    /** Number of paragraphs to show when collapsed. Default: 3 */
    collapsedParagraphs?: number;
}

export function PhishingEmailCard({
    emailContent,
    subject,
    from,
    to,
    collapsedParagraphs = 3,
}: PhishingEmailCardProps) {
    const [expanded, setExpanded] = useState(false);

    // Split into paragraphs for collapse logic
    const paragraphs = emailContent.split("\n\n");
    const isLong = paragraphs.length > collapsedParagraphs;
    const displayContent = expanded || !isLong
        ? emailContent
        : paragraphs.slice(0, collapsedParagraphs).join("\n\n");

    return (
        <div data-testid="phishing-email-card">
            {/* Section title with horizontal rule */}
            <div className="flex items-center gap-2 text-[11.5px] font-semibold tracking-[0.08em] uppercase text-text-muted mb-1">
                Original Phishing Email
                <span className="flex-1 h-px bg-border" />
            </div>

            {/* Card */}
            <div className="bg-surface border border-border2 rounded-lg overflow-hidden mt-2">
                {/* Card header with subject and from/to */}
                <div className="px-5 py-3.5 border-b border-border">
                    {subject && (
                        <div
                            className="font-mono text-sm font-semibold text-text"
                            data-testid="email-subject"
                        >
                            {subject}
                        </div>
                    )}
                    {(from || to) && (
                        <div className="font-mono text-[11.5px] text-text-muted mt-1">
                            {from && <>From: {from}</>}
                            {from && to && <>&nbsp;&middot;&nbsp;</>}
                            {to && <>To: {to}</>}
                        </div>
                    )}
                </div>

                {/* Email body */}
                <div className="px-5 py-5">
                    <div
                        className="text-[13px] text-text-secondary leading-[1.75] whitespace-pre-wrap"
                        data-testid="email-body"
                    >
                        {displayContent}
                    </div>
                </div>

                {/* Expand/collapse toggle */}
                {isLong && (
                    <button
                        className="flex items-center justify-center gap-1.5 w-full px-5 py-2.5 border-t border-border text-[12px] text-text-muted hover:text-text-secondary hover:bg-surface2 transition-colors cursor-pointer"
                        onClick={() => setExpanded(!expanded)}
                        data-testid="email-expand-toggle"
                    >
                        <svg
                            viewBox="0 0 16 16"
                            fill="none"
                            stroke="currentColor"
                            strokeWidth="1.5"
                            className="w-[13px] h-[13px]"
                        >
                            <path d={expanded ? "M4 10l4-4 4 4" : "M4 6l4 4 4-4"} />
                        </svg>
                        {expanded ? "Show less" : "Show full email"}
                    </button>
                )}
            </div>
        </div>
    );
}
