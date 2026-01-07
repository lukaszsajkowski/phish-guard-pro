"use client";

/**
 * Custom hook for API calls with client-side retry and exponential backoff.
 * 
 * Requirements: US-022 (API Error Handling)
 * - Automatic retry with exponential backoff (max 3 attempts)
 * - Preserves error state for display
 * - Session state not lost on error
 */

import { useState, useCallback, useRef } from "react";

export interface ApiError {
    message: string;
    errorCode?: string;
    retryAfter?: number;
    shouldRetry?: boolean;
}

export interface UseApiWithRetryOptions {
    /** Maximum number of retry attempts (default: 3) */
    maxRetries?: number;
    /** Base delay in milliseconds (default: 1000) */
    baseDelay?: number;
    /** Maximum delay cap in milliseconds (default: 10000) */
    maxDelay?: number;
}

export interface UseApiWithRetryResult<T> {
    /** Execute the API call with retry logic */
    execute: () => Promise<T | null>;
    /** Whether the request is currently loading */
    isLoading: boolean;
    /** Error object if the request failed */
    error: ApiError | null;
    /** Number of retry attempts made */
    retryCount: number;
    /** Reset error state for manual retry */
    reset: () => void;
    /** Trigger a manual retry */
    retry: () => Promise<T | null>;
}

/**
 * Parse error response from API into an ApiError object.
 */
async function parseErrorResponse(response: Response): Promise<ApiError> {
    try {
        const data = await response.json();
        return {
            message: data.error || "An unexpected error occurred. Please try again.",
            errorCode: data.error_code,
            retryAfter: data.retry_after,
            shouldRetry: data.should_retry ?? true,
        };
    } catch {
        // If we can't parse JSON, return a generic error
        return {
            message: getErrorMessageForStatus(response.status),
            shouldRetry: response.status >= 500,
        };
    }
}

/**
 * Get a user-friendly error message based on HTTP status code.
 */
function getErrorMessageForStatus(status: number): string {
    switch (status) {
        case 401:
            return "Session expired. Please log in again.";
        case 403:
            return "You don't have permission to perform this action.";
        case 404:
            return "The requested resource was not found.";
        case 429:
            return "The AI service is currently busy. Please try again in a moment.";
        case 500:
        case 502:
        case 503:
        case 504:
            return "Unable to connect to the AI service. Please try again.";
        default:
            return "An unexpected error occurred. Please try again.";
    }
}

/**
 * Check if an error is retryable (transient).
 */
function isRetryableError(status: number | undefined, apiError?: ApiError): boolean {
    // Check API response hint
    if (apiError?.shouldRetry !== undefined) {
        return apiError.shouldRetry;
    }

    // Network errors or server errors are generally retryable
    if (!status) return true; // Network error

    // 5xx and 429 are retryable
    return status >= 500 || status === 429;
}

/**
 * Custom hook for API calls with automatic retry and exponential backoff.
 * 
 * @example
 * ```tsx
 * const { execute, isLoading, error, retry, reset } = useApiWithRetry(
 *   async () => {
 *     const response = await fetch('/api/endpoint');
 *     if (!response.ok) throw response;
 *     return response.json();
 *   },
 *   { maxRetries: 3 }
 * );
 * 
 * // In render:
 * {error && <ApiError message={error.message} onRetry={retry} isRetrying={isLoading} />}
 * ```
 */
export function useApiWithRetry<T>(
    fetchFn: () => Promise<T>,
    options: UseApiWithRetryOptions = {}
): UseApiWithRetryResult<T> {
    const {
        maxRetries = 3,
        baseDelay = 1000,
        maxDelay = 10000
    } = options;

    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState<ApiError | null>(null);
    const [retryCount, setRetryCount] = useState(0);

    // Store the fetch function in a ref so we can retry
    const fetchFnRef = useRef(fetchFn);
    fetchFnRef.current = fetchFn;

    const reset = useCallback(() => {
        setError(null);
        setRetryCount(0);
    }, []);

    const execute = useCallback(async (): Promise<T | null> => {
        setIsLoading(true);
        setError(null);
        setRetryCount(0);

        let lastError: ApiError | null = null;
        let attempt = 0;

        while (attempt < maxRetries) {
            attempt++;
            setRetryCount(attempt);

            try {
                const result = await fetchFnRef.current();
                setIsLoading(false);
                setError(null);
                return result;
            } catch (err) {
                // Handle Response object (from fetch)
                if (err instanceof Response) {
                    lastError = await parseErrorResponse(err);

                    // Check if we should retry
                    if (!isRetryableError(err.status, lastError)) {
                        // Non-retryable error, fail immediately
                        setIsLoading(false);
                        setError(lastError);
                        return null;
                    }

                    // Retryable error
                    if (attempt < maxRetries) {
                        // Calculate delay with exponential backoff
                        const delay = lastError.retryAfter
                            ? lastError.retryAfter * 1000
                            : Math.min(baseDelay * Math.pow(2, attempt - 1), maxDelay);

                        await new Promise(resolve => setTimeout(resolve, delay));
                        continue;
                    }
                } else if (err instanceof Error) {
                    // Handle network errors or other thrown errors
                    lastError = {
                        message: err.message || "An unexpected error occurred. Please try again.",
                        shouldRetry: true,
                    };

                    if (attempt < maxRetries) {
                        const delay = Math.min(baseDelay * Math.pow(2, attempt - 1), maxDelay);
                        await new Promise(resolve => setTimeout(resolve, delay));
                        continue;
                    }
                } else {
                    // Unknown error type
                    lastError = {
                        message: "An unexpected error occurred. Please try again.",
                        shouldRetry: true,
                    };
                }
            }
        }

        // All retries exhausted
        setIsLoading(false);
        setError(lastError || {
            message: "Unable to connect to the service after multiple attempts. Please try again later.",
            shouldRetry: true,
        });
        return null;
    }, [maxRetries, baseDelay, maxDelay]);

    const retry = useCallback(async (): Promise<T | null> => {
        return execute();
    }, [execute]);

    return {
        execute,
        isLoading,
        error,
        retryCount,
        reset,
        retry,
    };
}
