"use client";

import { AlertTriangle, ArrowRight, FileText, Loader2 } from "lucide-react";
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

interface UnmaskingDialogProps {
    open: boolean;
    matchedPhrases: string[];
    confidence: number;
    onSummarize: () => void;
    onContinue: () => void;
    isLoading?: boolean;
}

/**
 * UnmaskingDialog - Shown when bot unmasking is detected (US-016)
 *
 * Displays when the scammer appears to have realized they're talking to a bot.
 * Provides two options:
 * - "Summarize" - Ends session and shows summary
 * - "Continue anyway" - Continues the conversation
 */
export function UnmaskingDialog({
    open,
    matchedPhrases,
    confidence,
    onSummarize,
    onContinue,
    isLoading = false,
}: UnmaskingDialogProps) {
    return (
        <AlertDialog open={open}>
            <AlertDialogContent className="max-w-md" data-testid="unmasking-dialog">
                <AlertDialogHeader>
                    <div className="flex items-center gap-2 mb-2">
                        <div className="flex-shrink-0 w-10 h-10 rounded-full bg-orange-500/10 flex items-center justify-center">
                            <AlertTriangle className="w-5 h-5 text-orange-500" />
                        </div>
                        <AlertDialogTitle className="text-lg">
                            Scammer May Have Ended Conversation
                        </AlertDialogTitle>
                    </div>
                    <AlertDialogDescription className="text-left space-y-3">
                        <p>
                            It appears the scammer may have realized they&apos;re talking to a bot
                            and ended the conversation.
                        </p>
                        {matchedPhrases.length > 0 && (
                            <div className="p-3 rounded-lg bg-muted/50 border border-border/50">
                                <p className="text-sm text-muted-foreground mb-2">
                                    Detected phrases:
                                </p>
                                <ul className="list-disc list-inside text-sm text-muted-foreground">
                                    {matchedPhrases.slice(0, 3).map((phrase, index) => (
                                        <li key={index} className="italic">
                                            &ldquo;{phrase}&rdquo;
                                        </li>
                                    ))}
                                </ul>
                                <p className="text-xs text-muted-foreground mt-2">
                                    Confidence: {Math.round(confidence * 100)}%
                                </p>
                            </div>
                        )}
                        <p className="text-sm text-muted-foreground">
                            Would you like to view the session summary or continue anyway?
                        </p>
                    </AlertDialogDescription>
                </AlertDialogHeader>
                <AlertDialogFooter className="flex-col sm:flex-row gap-2 sm:gap-0">
                    <AlertDialogCancel
                        onClick={onContinue}
                        className="w-full sm:w-auto"
                        data-testid="unmasking-continue-button"
                        disabled={isLoading}
                    >
                        <ArrowRight className="w-4 h-4 mr-2" />
                        Continue anyway
                    </AlertDialogCancel>
                    <AlertDialogAction
                        onClick={onSummarize}
                        disabled={isLoading}
                        className="w-full sm:w-auto"
                        data-testid="unmasking-summarize-button"
                    >
                        {isLoading ? (
                            <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                        ) : (
                            <FileText className="w-4 h-4 mr-2" />
                        )}
                        {isLoading ? "Loading..." : "Summarize"}
                    </AlertDialogAction>
                </AlertDialogFooter>
            </AlertDialogContent>
        </AlertDialog>
    );
}
