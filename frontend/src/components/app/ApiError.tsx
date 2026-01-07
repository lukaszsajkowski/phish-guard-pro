"use client";

/**
 * ApiError component for displaying user-friendly error messages.
 * 
 * Requirements: US-022 (API Error Handling)
 * - Shows error message (not stack traces)
 * - Provides "Try again" button with loading state
 * - Optional help text for persistent issues
 */

import { AlertCircle, RefreshCw, Loader2 } from "lucide-react";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";

export interface ApiErrorProps {
    /** User-friendly error message to display */
    message?: string;
    /** Title for the error alert (default: "Something went wrong") */
    title?: string;
    /** Callback function when "Try again" is clicked */
    onRetry?: () => void;
    /** Whether a retry is currently in progress */
    isRetrying?: boolean;
    /** Whether to show help text about checking connection */
    showHelpText?: boolean;
    /** Custom label for the retry button */
    retryLabel?: string;
    /** Additional CSS class names */
    className?: string;
    /** Test ID for E2E testing */
    "data-testid"?: string;
}

export function ApiError({
    message = "Unable to connect to the service. Please try again.",
    title = "Something went wrong",
    onRetry,
    isRetrying = false,
    showHelpText = true,
    retryLabel = "Try again",
    className = "",
    "data-testid": testId = "api-error",
}: ApiErrorProps) {
    return (
        <Alert
            variant="destructive"
            className={`animate-in fade-in slide-in-from-top-2 duration-300 ${className}`}
            data-testid={testId}
        >
            <AlertCircle className="h-4 w-4" />
            <AlertTitle>{title}</AlertTitle>
            <AlertDescription className="mt-2">
                <p data-testid={`${testId}-message`}>{message}</p>

                {showHelpText && (
                    <p className="mt-2 text-xs text-muted-foreground">
                        If this issue persists, please check your internet connection or try again later.
                    </p>
                )}

                {onRetry && (
                    <Button
                        variant="outline"
                        size="sm"
                        onClick={onRetry}
                        disabled={isRetrying}
                        className="mt-3"
                        data-testid={`${testId}-retry-button`}
                    >
                        {isRetrying ? (
                            <>
                                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                                Retrying...
                            </>
                        ) : (
                            <>
                                <RefreshCw className="mr-2 h-4 w-4" />
                                {retryLabel}
                            </>
                        )}
                    </Button>
                )}
            </AlertDescription>
        </Alert>
    );
}

/**
 * Pre-configured error displays for common scenarios.
 */

export function RateLimitError({
    onRetry,
    isRetrying,
    retryAfter,
}: Pick<ApiErrorProps, "onRetry" | "isRetrying"> & { retryAfter?: number }) {
    return (
        <ApiError
            title="Service Busy"
            message={`The AI service is currently busy. ${retryAfter ? `Please wait ${retryAfter} seconds before trying again.` : "Please try again in a moment."}`}
            onRetry={onRetry}
            isRetrying={isRetrying}
            retryLabel="Try again (wait a moment)"
            showHelpText={false}
            data-testid="rate-limit-error"
        />
    );
}

export function ConnectionError({
    onRetry,
    isRetrying,
}: Pick<ApiErrorProps, "onRetry" | "isRetrying">) {
    return (
        <ApiError
            title="Connection Error"
            message="Unable to connect to the AI service after multiple attempts. Please check your connection and try again."
            onRetry={onRetry}
            isRetrying={isRetrying}
            showHelpText={true}
            data-testid="connection-error"
        />
    );
}
