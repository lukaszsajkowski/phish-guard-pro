"use client";

import Link from "next/link";
import { Shield, LogOut, Loader2, RotateCcw, FileText, History } from "lucide-react";
import { User } from "@supabase/supabase-js";
import { Button } from "@/components/ui/button";

interface AppHeaderProps {
    user: User;
    onSignOut: () => void;
    isSigningOut?: boolean;
    showSessionActions?: boolean;
    sessionId?: string | null;
    onEndSession?: () => void;
    onNewSession?: () => void;
    isEndingSession?: boolean;
}

export function AppHeader({
    user,
    onSignOut,
    isSigningOut = false,
    showSessionActions = false,
    sessionId,
    onEndSession,
    onNewSession,
    isEndingSession = false,
}: AppHeaderProps) {
    return (
        <header className="border-b border-border/40 bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
            <div className="container flex h-16 items-center justify-between px-4">
                <Link href="/dashboard" className="flex items-center gap-2">
                    <Shield className="h-8 w-8 text-primary" />
                    <span className="text-xl font-bold tracking-tight">
                        PhishGuard Pro
                    </span>
                </Link>
                <div className="flex items-center gap-4">
                    {/* End Session button - visible when session is active */}
                    {showSessionActions && sessionId && (
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
                    )}

                    {/* New Session button - visible when session is active */}
                    {showSessionActions && sessionId && (
                        <Button
                            variant="ghost"
                            size="sm"
                            onClick={onNewSession}
                            data-testid="new-session-header-button"
                        >
                            <RotateCcw className="h-4 w-4 mr-2" />
                            New Session
                        </Button>
                    )}

                    {/* History link */}
                    <Link
                        href="/history"
                        className="flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground transition-colors"
                        data-testid="history-link"
                    >
                        <History className="h-4 w-4" />
                        <span className="hidden sm:inline">History</span>
                    </Link>

                    <span className="text-sm text-muted-foreground">
                        {user.email}
                    </span>
                    <button
                        id="signout-button"
                        onClick={onSignOut}
                        disabled={isSigningOut}
                        className="inline-flex items-center gap-2 rounded-md border border-border bg-background px-4 py-2 text-sm font-medium transition-colors hover:bg-muted disabled:pointer-events-none disabled:opacity-50"
                    >
                        {isSigningOut ? (
                            <>
                                <Loader2 className="h-4 w-4 animate-spin" />
                                Signing out...
                            </>
                        ) : (
                            <>
                                <LogOut className="h-4 w-4" />
                                Sign out
                            </>
                        )}
                    </button>
                </div>
            </div>
        </header>
    );
}
