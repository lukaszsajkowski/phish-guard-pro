import { renderHook, act, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { useEnrichment, deriveThreatAssessment } from "../useEnrichment";
import type { EnrichmentResponse } from "@/types/schemas";

// ---------------------------------------------------------------------------
// deriveThreatAssessment – pure function tests
// ---------------------------------------------------------------------------

describe("deriveThreatAssessment", () => {
    it("returns malicious reputation for BTC with malicious payload", () => {
        const res: EnrichmentResponse = {
            status: "ok",
            source: "btc_mempool",
            ioc_type: "btc",
            payload: { reputation: "malicious", report_count: 5 },
            cached: false,
            latency_ms: 120,
        };
        const result = deriveThreatAssessment(res);
        expect(result.reputation).toBe("malicious");
        // 70 + (5/20)*30 = 70 + 7.5 = 78 (rounded)
        expect(result.threat_score).toBe(78);
    });

    it("caps malicious BTC score at 100 for high report counts", () => {
        const res: EnrichmentResponse = {
            status: "ok",
            source: "btc_mempool",
            ioc_type: "btc",
            payload: { reputation: "malicious", report_count: 50 },
            cached: false,
            latency_ms: 80,
        };
        const result = deriveThreatAssessment(res);
        expect(result.threat_score).toBe(100);
    });

    it("returns suspicious reputation for BTC with suspicious payload", () => {
        const res: EnrichmentResponse = {
            status: "ok",
            source: "btc_mempool",
            ioc_type: "btc",
            payload: { reputation: "suspicious", report_count: 2 },
            cached: false,
            latency_ms: 90,
        };
        const result = deriveThreatAssessment(res);
        expect(result.reputation).toBe("suspicious");
        // 40 + 2*10 = 60
        expect(result.threat_score).toBe(60);
    });

    it("caps suspicious BTC score at 69", () => {
        const res: EnrichmentResponse = {
            status: "ok",
            source: "btc_mempool",
            ioc_type: "btc",
            payload: { reputation: "suspicious", report_count: 10 },
            cached: false,
            latency_ms: 90,
        };
        const result = deriveThreatAssessment(res);
        expect(result.threat_score).toBe(69);
    });

    it("returns low score for BTC unknown with tx activity", () => {
        const res: EnrichmentResponse = {
            status: "ok",
            source: "btc_mempool",
            ioc_type: "btc",
            payload: { reputation: "unknown", tx_count: 3 },
            cached: false,
            latency_ms: 100,
        };
        const result = deriveThreatAssessment(res);
        expect(result.reputation).toBe("unknown");
        expect(result.threat_score).toBe(15);
    });

    it("returns minimal score for BTC unknown with no activity", () => {
        const res: EnrichmentResponse = {
            status: "ok",
            source: "btc_mempool",
            ioc_type: "btc",
            payload: { reputation: "unknown", tx_count: 0 },
            cached: false,
            latency_ms: 100,
        };
        const result = deriveThreatAssessment(res);
        expect(result.threat_score).toBe(5);
    });

    it("returns 0 score for non-ok status", () => {
        const res: EnrichmentResponse = {
            status: "error",
            source: "btc_mempool",
            ioc_type: "btc",
            payload: null,
            cached: false,
            latency_ms: 0,
        };
        const result = deriveThreatAssessment(res);
        expect(result.threat_score).toBe(0);
        expect(result.reputation).toBe("unknown");
    });

    it("uses generic fallback for non-BTC malicious", () => {
        const res: EnrichmentResponse = {
            status: "ok",
            source: "url_source",
            ioc_type: "url",
            payload: { reputation: "malicious" },
            cached: false,
            latency_ms: 50,
        };
        const result = deriveThreatAssessment(res);
        expect(result.threat_score).toBe(90);
        expect(result.reputation).toBe("malicious");
    });

    it("uses generic fallback for non-BTC clean", () => {
        const res: EnrichmentResponse = {
            status: "ok",
            source: "url_source",
            ioc_type: "url",
            payload: { reputation: "clean" },
            cached: false,
            latency_ms: 50,
        };
        const result = deriveThreatAssessment(res);
        expect(result.threat_score).toBe(10);
        expect(result.reputation).toBe("clean");
    });

    it("returns unknown for generic with no reputation in payload", () => {
        const res: EnrichmentResponse = {
            status: "ok",
            source: "generic",
            ioc_type: "phone",
            payload: { some_data: true },
            cached: false,
            latency_ms: 50,
        };
        const result = deriveThreatAssessment(res);
        expect(result.threat_score).toBe(0);
        expect(result.reputation).toBe("unknown");
    });

    it("handles null payload gracefully", () => {
        const res: EnrichmentResponse = {
            status: "ok",
            source: "btc_mempool",
            ioc_type: "btc",
            payload: null,
            cached: false,
            latency_ms: 100,
        };
        const result = deriveThreatAssessment(res);
        // null payload -> defaults: reputation unknown, tx_count 0
        expect(result.reputation).toBe("unknown");
        expect(result.threat_score).toBe(5);
    });
});

// ---------------------------------------------------------------------------
// useEnrichment hook tests
// ---------------------------------------------------------------------------

describe("useEnrichment", () => {
    const mockGetAccessToken = vi.fn<() => Promise<string | null>>();

    beforeEach(() => {
        vi.resetAllMocks();
        mockGetAccessToken.mockResolvedValue("test-jwt-token");
    });

    afterEach(() => {
        vi.restoreAllMocks();
    });

    it("initialises with empty enrichment states", () => {
        const { result } = renderHook(() => useEnrichment(mockGetAccessToken));
        expect(result.current.enrichmentStates).toEqual({});
    });

    it("getKey produces deterministic keys", () => {
        const { result } = renderHook(() => useEnrichment(mockGetAccessToken));
        expect(result.current.getKey("btc", "abc123")).toBe("btc::abc123");
    });

    it("transitions to loading state when enrich is called", async () => {
        // Never resolve the fetch so we stay in loading
        vi.spyOn(globalThis, "fetch").mockImplementation(
            () => new Promise(() => {}),
        );

        const { result } = renderHook(() => useEnrichment(mockGetAccessToken));

        act(() => {
            result.current.enrich("btc", "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa");
        });

        await waitFor(() => {
            const key = result.current.getKey(
                "btc",
                "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa",
            );
            expect(result.current.enrichmentStates[key]).toEqual({
                status: "loading",
            });
        });
    });

    it("transitions to success state on successful fetch", async () => {
        const mockResponse: EnrichmentResponse = {
            status: "ok",
            source: "btc_mempool",
            ioc_type: "btc",
            payload: { reputation: "malicious", report_count: 3 },
            cached: false,
            latency_ms: 150,
        };

        vi.spyOn(globalThis, "fetch").mockResolvedValue({
            ok: true,
            json: () => Promise.resolve(mockResponse),
        } as Response);

        const { result } = renderHook(() => useEnrichment(mockGetAccessToken));

        await act(async () => {
            await result.current.enrich("btc", "1A1zP1");
        });

        const key = result.current.getKey("btc", "1A1zP1");
        expect(result.current.enrichmentStates[key]).toEqual({
            status: "success",
            data: mockResponse,
        });
    });

    it("passes Authorization header with token", async () => {
        const fetchSpy = vi.spyOn(globalThis, "fetch").mockResolvedValue({
            ok: true,
            json: () =>
                Promise.resolve({
                    status: "ok",
                    source: "btc_mempool",
                    ioc_type: "btc",
                    payload: null,
                    cached: false,
                    latency_ms: 0,
                }),
        } as Response);

        const { result } = renderHook(() => useEnrichment(mockGetAccessToken));

        await act(async () => {
            await result.current.enrich("btc", "abc");
        });

        expect(fetchSpy).toHaveBeenCalledWith(
            expect.stringContaining("/api/v1/enrichment/btc/abc"),
            expect.objectContaining({
                headers: { Authorization: "Bearer test-jwt-token" },
            }),
        );
    });

    it("normalises btc_wallet type to btc in API call", async () => {
        const fetchSpy = vi.spyOn(globalThis, "fetch").mockResolvedValue({
            ok: true,
            json: () =>
                Promise.resolve({
                    status: "ok",
                    source: "btc_mempool",
                    ioc_type: "btc",
                    payload: null,
                    cached: false,
                    latency_ms: 0,
                }),
        } as Response);

        const { result } = renderHook(() => useEnrichment(mockGetAccessToken));

        await act(async () => {
            await result.current.enrich("btc_wallet", "bc1qxyz");
        });

        expect(fetchSpy).toHaveBeenCalledWith(
            expect.stringContaining("/api/v1/enrichment/btc/"),
            expect.anything(),
        );
    });

    it("transitions to error state on HTTP error", async () => {
        vi.spyOn(globalThis, "fetch").mockResolvedValue({
            ok: false,
            status: 500,
            text: () => Promise.resolve("Internal Server Error"),
        } as Response);

        const { result } = renderHook(() => useEnrichment(mockGetAccessToken));

        await act(async () => {
            await result.current.enrich("btc", "abc");
        });

        const key = result.current.getKey("btc", "abc");
        const state = result.current.enrichmentStates[key];
        expect(state.status).toBe("error");
        if (state.status === "error") {
            expect(state.error).toContain("500");
        }
    });

    it("shows 'Unsupported IOC type' for 400 errors", async () => {
        vi.spyOn(globalThis, "fetch").mockResolvedValue({
            ok: false,
            status: 400,
            text: () => Promise.resolve("Bad Request"),
        } as Response);

        const { result } = renderHook(() => useEnrichment(mockGetAccessToken));

        await act(async () => {
            await result.current.enrich("phone", "123");
        });

        const key = result.current.getKey("phone", "123");
        const state = result.current.enrichmentStates[key];
        expect(state.status).toBe("error");
        if (state.status === "error") {
            expect(state.error).toBe("Unsupported IOC type");
        }
    });

    it("transitions to error on network failure", async () => {
        vi.spyOn(globalThis, "fetch").mockRejectedValue(
            new Error("Network error"),
        );

        const { result } = renderHook(() => useEnrichment(mockGetAccessToken));

        await act(async () => {
            await result.current.enrich("btc", "abc");
        });

        const key = result.current.getKey("btc", "abc");
        const state = result.current.enrichmentStates[key];
        expect(state.status).toBe("error");
        if (state.status === "error") {
            expect(state.error).toBe("Network error");
        }
    });

    it("transitions to error when not authenticated", async () => {
        mockGetAccessToken.mockResolvedValue(null);

        const { result } = renderHook(() => useEnrichment(mockGetAccessToken));

        await act(async () => {
            await result.current.enrich("btc", "abc");
        });

        const key = result.current.getKey("btc", "abc");
        const state = result.current.enrichmentStates[key];
        expect(state.status).toBe("error");
        if (state.status === "error") {
            expect(state.error).toBe("Not authenticated");
        }
    });

    it("allows retry after error (re-calling enrich)", async () => {
        // First call: fail
        const fetchSpy = vi.spyOn(globalThis, "fetch").mockRejectedValueOnce(
            new Error("Timeout"),
        );

        const { result } = renderHook(() => useEnrichment(mockGetAccessToken));

        await act(async () => {
            await result.current.enrich("btc", "abc");
        });

        const key = result.current.getKey("btc", "abc");
        expect(result.current.enrichmentStates[key].status).toBe("error");

        // Second call: succeed
        fetchSpy.mockResolvedValueOnce({
            ok: true,
            json: () =>
                Promise.resolve({
                    status: "ok",
                    source: "btc_mempool",
                    ioc_type: "btc",
                    payload: { reputation: "clean" },
                    cached: false,
                    latency_ms: 50,
                }),
        } as Response);

        await act(async () => {
            await result.current.enrich("btc", "abc");
        });

        expect(result.current.enrichmentStates[key].status).toBe("success");
    });
});
