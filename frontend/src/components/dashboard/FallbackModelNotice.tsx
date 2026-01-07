"use client";

import { Zap } from "lucide-react";

interface FallbackModelNoticeProps {
    className?: string;
}

/**
 * Notice component displayed when the fallback LLM model is used (US-023).
 *
 * This provides a non-intrusive info banner to inform users that
 * the system switched to a faster (but potentially less accurate) model
 * due to primary model unavailability.
 */
export function FallbackModelNotice({ className }: FallbackModelNoticeProps) {
    return (
        <div
            className={`flex items-center gap-2 px-3 py-2 bg-blue-500/10 border border-blue-500/20 rounded-lg text-sm text-blue-600 dark:text-blue-400 ${className || ""}`}
            data-testid="fallback-model-notice"
            role="status"
            aria-live="polite"
        >
            <Zap className="w-4 h-4 flex-shrink-0" />
            <span>Using faster model for this response</span>
        </div>
    );
}
