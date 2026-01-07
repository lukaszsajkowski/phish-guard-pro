"use client";

import { AlertCircle, FileText, X } from "lucide-react";
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

interface EndSessionDialogProps {
    open: boolean;
    onOpenChange: (open: boolean) => void;
    onConfirm: () => void;
    isLoading?: boolean;
}

/**
 * EndSessionDialog - Confirmation modal for manual session end (US-017)
 *
 * Warns user about ending the session and offers confirmation.
 */
export function EndSessionDialog({
    open,
    onOpenChange,
    onConfirm,
    isLoading = false,
}: EndSessionDialogProps) {
    return (
        <AlertDialog open={open} onOpenChange={onOpenChange}>
            <AlertDialogContent className="max-w-md" data-testid="end-session-dialog">
                <AlertDialogHeader>
                    <div className="flex items-center gap-2 mb-2">
                        <div className="flex-shrink-0 w-10 h-10 rounded-full bg-destructive/10 flex items-center justify-center">
                            <AlertCircle className="w-5 h-5 text-destructive" />
                        </div>
                        <AlertDialogTitle className="text-lg">
                            End Session?
                        </AlertDialogTitle>
                    </div>
                    <AlertDialogDescription asChild>
                        <div className="text-muted-foreground text-sm text-left space-y-3">
                            <p>
                                Are you sure you want to end this session? This will:
                            </p>
                            <ul className="list-disc list-inside space-y-1">
                                <li>Generate a final summary report</li>
                                <li>Archive the conversation</li>
                                <li>Make the session read-only</li>
                            </ul>
                            <div className="p-3 rounded-lg bg-muted/50 border border-border/50">
                                <div className="flex items-start gap-2">
                                    <AlertCircle className="w-4 h-4 text-muted-foreground mt-0.5 flex-shrink-0" />
                                    <span>
                                        You can export your data (JSON/CSV) from the summary page.
                                    </span>
                                </div>
                            </div>
                        </div>
                    </AlertDialogDescription>
                </AlertDialogHeader>
                <AlertDialogFooter className="flex-col sm:flex-row gap-2 sm:gap-0">
                    <AlertDialogCancel
                        className="w-full sm:w-auto"
                        data-testid="end-session-cancel-button"
                        disabled={isLoading}
                    >
                        <X className="w-4 h-4 mr-2" />
                        Cancel
                    </AlertDialogCancel>
                    <AlertDialogAction
                        onClick={(e) => {
                            e.preventDefault();
                            onConfirm();
                        }}
                        disabled={isLoading}
                        className="w-full sm:w-auto bg-destructive text-destructive-foreground hover:bg-destructive/90"
                        data-testid="end-session-confirm-button"
                    >
                        <FileText className="w-4 h-4 mr-2" />
                        {isLoading ? "Ending..." : "End and Summarize"}
                    </AlertDialogAction>
                </AlertDialogFooter>
            </AlertDialogContent>
        </AlertDialog>
    );
}
