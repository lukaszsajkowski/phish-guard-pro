"use client";

/**
 * Custom hook for per-IOC enrichment (US-038).
 *
 * Manages enrichment state for each IOC independently, calls the backend
 * GET /api/v1/enrichment/{ioc_type}/{value} endpoint, and derives a
 * threat assessment (score + reputation) from the response payload.
 */

import { useState, useCallback } from "react";
import type {
    EnrichmentResponse,
    EnrichmentState,
    ThreatAssessment,
    ReputationLabel,
} from "@/types/schemas";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// ---------------------------------------------------------------------------
// Threat-score derivation
// ---------------------------------------------------------------------------

/**
 * Derive a 0-100 threat score and reputation label from an enrichment
 * response payload.  Source-specific heuristics first, then a generic
 * fallback based on the enrichment status.
 */
export function deriveThreatAssessment(
    res: EnrichmentResponse,
): ThreatAssessment {
    const payload = res.payload ?? {};

    // Source-specific: BTC enrichment (btc_mempool source)
    if (res.ioc_type === "btc" && res.status === "ok") {
        const reputation = (payload.reputation as ReputationLabel) ?? "unknown";
        const reportCount =
            typeof payload.report_count === "number" ? payload.report_count : 0;

        let score: number;
        if (reputation === "malicious") {
            // 70-100 proportional to report count (cap at 20 reports)
            score = Math.min(100, 70 + Math.round((reportCount / 20) * 30));
        } else if (reputation === "suspicious") {
            // 40-69
            score = Math.min(69, 40 + reportCount * 10);
        } else {
            // unknown — check if the wallet has any activity
            const txCount =
                typeof payload.tx_count === "number" ? payload.tx_count : 0;
            score = txCount > 0 ? 15 : 5;
        }

        return { threat_score: score, reputation };
    }

    // Generic fallback for any IOC type
    if (res.status !== "ok") {
        return { threat_score: 0, reputation: "unknown" };
    }

    // If payload explicitly includes a reputation field, use it
    const rep = payload.reputation as ReputationLabel | undefined;
    if (rep === "malicious") return { threat_score: 90, reputation: "malicious" };
    if (rep === "suspicious") return { threat_score: 50, reputation: "suspicious" };
    if (rep === "clean") return { threat_score: 10, reputation: "clean" };

    return { threat_score: 0, reputation: "unknown" };
}

// ---------------------------------------------------------------------------
// Hook
// ---------------------------------------------------------------------------

export interface UseEnrichmentReturn {
    /** Map of IOC key -> enrichment state */
    enrichmentStates: Record<string, EnrichmentState>;
    /** Trigger enrichment for one IOC */
    enrich: (iocType: string, iocValue: string) => Promise<void>;
    /** Get a stable map key for an IOC */
    getKey: (iocType: string, iocValue: string) => string;
}

/**
 * Hook that manages per-IOC enrichment lifecycle.
 *
 * @param getAccessToken - async function returning a valid JWT, or null if
 *   the user is not authenticated.  Follows the same pattern as the dashboard
 *   page (`supabase.auth.getSession()`).
 */
export function useEnrichment(
    getAccessToken: () => Promise<string | null>,
): UseEnrichmentReturn {
    const [enrichmentStates, setEnrichmentStates] = useState<
        Record<string, EnrichmentState>
    >({});

    const getKey = useCallback(
        (iocType: string, iocValue: string) => `${iocType}::${iocValue}`,
        [],
    );

    const enrich = useCallback(
        async (iocType: string, iocValue: string) => {
            const key = getKey(iocType, iocValue);

            // Normalise IOC type for the backend (btc_wallet -> btc)
            const apiType = iocType === "btc_wallet" ? "btc" : iocType;

            setEnrichmentStates((prev) => ({
                ...prev,
                [key]: { status: "loading" },
            }));

            try {
                const token = await getAccessToken();
                if (!token) {
                    setEnrichmentStates((prev) => ({
                        ...prev,
                        [key]: { status: "error", error: "Not authenticated" },
                    }));
                    return;
                }

                const response = await fetch(
                    `${API_URL}/api/v1/enrichment/${encodeURIComponent(apiType)}/${encodeURIComponent(iocValue)}`,
                    {
                        headers: {
                            Authorization: `Bearer ${token}`,
                        },
                    },
                );

                if (!response.ok) {
                    const errorText = await response.text().catch(() => "Unknown error");
                    setEnrichmentStates((prev) => ({
                        ...prev,
                        [key]: {
                            status: "error",
                            error:
                                response.status === 400
                                    ? "Unsupported IOC type"
                                    : `Enrichment failed (${response.status}): ${errorText}`,
                        },
                    }));
                    return;
                }

                const data: EnrichmentResponse = await response.json();

                setEnrichmentStates((prev) => ({
                    ...prev,
                    [key]: { status: "success", data },
                }));
            } catch (err) {
                setEnrichmentStates((prev) => ({
                    ...prev,
                    [key]: {
                        status: "error",
                        error:
                            err instanceof Error
                                ? err.message
                                : "Network error. Please try again.",
                    },
                }));
            }
        },
        [getAccessToken, getKey],
    );

    return { enrichmentStates, enrich, getKey };
}
