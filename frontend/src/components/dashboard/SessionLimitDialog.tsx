"use client";

import { AlertCircle, ArrowRight, FileText, Timer } from "lucide-react";
import {
    AlertDialog,
    AlertDialogAction,
    AlertDialogCancel,
    AlertDialogContent,
    AlertDialogDescription,
    AlertDialogFooter,
    AlertDialogHeader,
    AlertDialogTitle,
} from "@/components/ui/alert-dialog";

interface SessionLimitDialogProps {
    open: boolean;
    turnCount: number;
    turnLimit: number;
    onContinue: () => void;
    onEndSession: () => void;
    isExtending?: boolean;
}

/**
 * SessionLimitDialog - Shown when conversation reaches the turn limit (US-015)
 *
 * Provides two options:
 * - "Continue (+10 turns)" - Extends the session limit
 * - "End and summarize" - Ends the session and generates a summary
 */
export function SessionLimitDialog({
    open,
    turnCount,
    turnLimit,
    onContinue,
    onEndSession,
    isExtending = false,
}: SessionLimitDialogProps) {
    return (
        <AlertDialog open={open}>
            <AlertDialogContent className="max-w-md">
                <AlertDialogHeader>
                    <div className="flex items-center gap-2 mb-2">
                        <div className="flex-shrink-0 w-10 h-10 rounded-full bg-amber-500/10 flex items-center justify-center">
                            <Timer className="w-5 h-5 text-amber-500" />
                        </div>
                        <AlertDialogTitle className="text-lg">
                            Session Limit Reached
                        </AlertDialogTitle>
                    </div>
                    <AlertDialogDescription className="text-left space-y-3">
                        <p>
                            You've reached <strong>{turnCount} turns</strong> in this conversation
                            (limit: {turnLimit}).
                        </p>
                        <div className="p-3 rounded-lg bg-muted/50 border border-border/50">
                            <div className="flex items-start gap-2">
                                <AlertCircle className="w-4 h-4 text-muted-foreground mt-0.5 flex-shrink-0" />
                                <p className="text-sm text-muted-foreground">
                                    Extending the session allows you to continue waste
                                    the scammer's time and collect more intel.
                                </p>
                            </div>
                        </div>
                    </AlertDialogDescription>
                </AlertDialogHeader>
                <AlertDialogFooter className="flex-col sm:flex-row gap-2 sm:gap-0">
                    <AlertDialogCancel
                        onClick={onEndSession}
                        className="w-full sm:w-auto"
                        data-testid="end-session-button"
                    >
                        <FileText className="w-4 h-4 mr-2" />
                        End and summarize
                    </AlertDialogCancel>
                    <AlertDialogAction
                        onClick={onContinue}
                        disabled={isExtending}
                        className="w-full sm:w-auto"
                        data-testid="continue-session-button"
                    >
                        <ArrowRight className="w-4 h-4 mr-2" />
                        {isExtending ? "Extending..." : "Continue (+10 turns)"}
                    </AlertDialogAction>
                </AlertDialogFooter>
            </AlertDialogContent>
        </AlertDialog>
    );
}
