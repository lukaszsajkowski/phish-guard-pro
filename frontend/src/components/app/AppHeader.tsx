"use client";

import { RotateCcw, FileText } from "lucide-react";
import { Button } from "@/components/ui/button";

interface AppHeaderProps {
    showSessionActions?: boolean;
    sessionId?: string | null;
    onEndSession?: () => void;
    onNewSession?: () => void;
    isEndingSession?: boolean;
}

export function AppHeader({
    showSessionActions = false,
    sessionId,
    onEndSession,
    onNewSession,
    isEndingSession = false,
}: AppHeaderProps) {
    // Only render header when there are actions to show
    if (!showSessionActions || !sessionId) {
        return null;
    }

    return (
        <header className="border-b border-border/40 bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
            <div className="flex h-14 items-center justify-end px-4">
                <div className="flex items-center gap-3">
                    {/* End Session button */}
                    <Button
                        variant="outline"
                        size="sm"
                        onClick={onEndSession}
                        disabled={isEndingSession}
                        data-testid="end-session-header-button"
                    >
                        <FileText className="h-4 w-4 mr-2" />
                        End session
                    </Button>

                    {/* New Session button */}
                    <Button
                        variant="ghost"
                        size="sm"
                        onClick={onNewSession}
                        data-testid="new-session-header-button"
                    >
                        <RotateCcw className="h-4 w-4 mr-2" />
                        New Session
                    </Button>
                </div>
            </div>
        </header>
    );
}
