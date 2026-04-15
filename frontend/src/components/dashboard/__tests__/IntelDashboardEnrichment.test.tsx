import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { IntelDashboard } from "../IntelDashboard";
import type { ExtractedIOC, EnrichmentResponse } from "@/types/schemas";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const mockGetAccessToken = vi.fn<() => Promise<string | null>>();

const btcIoc: ExtractedIOC = {
    id: "ioc-1",
    type: "btc",
    value: "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa",
    is_high_value: true,
};

const ibanIoc: ExtractedIOC = {
    id: "ioc-2",
    type: "iban",
    value: "DE89370400440532013000",
    is_high_value: false,
};

function createSuccessResponse(
    overrides: Partial<EnrichmentResponse> = {},
): EnrichmentResponse {
    return {
        status: "ok",
        source: "btc_mempool",
        ioc_type: "btc",
        payload: { reputation: "malicious", report_count: 5, tx_count: 42 },
        cached: false,
        latency_ms: 150,
        ...overrides,
    };
}

function mockFetchSuccess(response: EnrichmentResponse) {
    vi.spyOn(globalThis, "fetch").mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(response),
    } as Response);
}

function renderDashboard(iocs: ExtractedIOC[] = [btcIoc]) {
    return render(
        <IntelDashboard
            iocs={iocs}
            attackType="ceo_fraud"
            confidence={95}
            riskScore={7}
            getAccessToken={mockGetAccessToken}
        />,
    );
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe("IntelDashboard – Enrichment UI", () => {
    beforeEach(() => {
        vi.resetAllMocks();
        mockGetAccessToken.mockResolvedValue("test-jwt-token");
    });

    afterEach(() => {
        vi.restoreAllMocks();
    });

    // ---- Enrich button visibility ----

    describe("Enrich button", () => {
        it("renders an Enrich button for each IOC card", () => {
            renderDashboard([btcIoc, ibanIoc]);

            expect(screen.getByTestId("enrich-button-btc")).toBeInTheDocument();
            expect(screen.getByTestId("enrich-button-iban")).toBeInTheDocument();
        });

        it("does NOT render Enrich buttons when getAccessToken is not provided", () => {
            render(
                <IntelDashboard
                    iocs={[btcIoc]}
                    attackType="ceo_fraud"
                    confidence={95}
                    riskScore={7}
                />,
            );

            expect(
                screen.queryByTestId("enrich-button-btc"),
            ).not.toBeInTheDocument();
        });
    });

    // ---- Loading state ----

    describe("Loading state", () => {
        it("shows loading spinner when enrichment is in-flight", async () => {
            // Fetch that never resolves keeps us in loading state
            vi.spyOn(globalThis, "fetch").mockImplementation(
                () => new Promise(() => {}),
            );

            renderDashboard();

            await userEvent.click(screen.getByTestId("enrich-button-btc"));

            expect(
                screen.getByTestId("enrich-loading-btc"),
            ).toBeInTheDocument();
            expect(screen.getByText("Enriching...")).toBeInTheDocument();
        });

        it("hides the Enrich button while loading", async () => {
            vi.spyOn(globalThis, "fetch").mockImplementation(
                () => new Promise(() => {}),
            );

            renderDashboard();

            await userEvent.click(screen.getByTestId("enrich-button-btc"));

            expect(
                screen.queryByTestId("enrich-button-btc"),
            ).not.toBeInTheDocument();
        });
    });

    // ---- Success state ----

    describe("Success – threat score", () => {
        it("renders threat score with red color for malicious (score > 66)", async () => {
            mockFetchSuccess(createSuccessResponse());

            renderDashboard();
            await userEvent.click(screen.getByTestId("enrich-button-btc"));

            const scoreEl = screen.getByTestId("threat-score-btc");
            expect(scoreEl).toBeInTheDocument();
            // Score = 78 (malicious with 5 reports)
            expect(scoreEl).toHaveTextContent("78");
            // The score value should have red color class
            const boldSpan = within(scoreEl).getByText("78");
            expect(boldSpan).toHaveClass("text-red-500");
        });

        it("renders threat score with yellow color for suspicious (34-66)", async () => {
            mockFetchSuccess(
                createSuccessResponse({
                    payload: { reputation: "suspicious", report_count: 1 },
                }),
            );

            renderDashboard();
            await userEvent.click(screen.getByTestId("enrich-button-btc"));

            const scoreEl = screen.getByTestId("threat-score-btc");
            // 40 + 1*10 = 50
            expect(scoreEl).toHaveTextContent("50");
            const boldSpan = within(scoreEl).getByText("50");
            expect(boldSpan).toHaveClass("text-yellow-500");
        });

        it("renders threat score with green color for clean (0-33)", async () => {
            mockFetchSuccess(
                createSuccessResponse({
                    payload: { reputation: "unknown", tx_count: 1 },
                }),
            );

            renderDashboard();
            await userEvent.click(screen.getByTestId("enrich-button-btc"));

            const scoreEl = screen.getByTestId("threat-score-btc");
            // unknown with tx_count > 0 => 15
            expect(scoreEl).toHaveTextContent("15");
            const boldSpan = within(scoreEl).getByText("15");
            expect(boldSpan).toHaveClass("text-green-500");
        });
    });

    describe("Success – reputation badge", () => {
        it("shows Malicious badge with red styling", async () => {
            mockFetchSuccess(createSuccessResponse());

            renderDashboard();
            await userEvent.click(screen.getByTestId("enrich-button-btc"));

            const badge = screen.getByTestId("reputation-badge-btc");
            expect(badge).toHaveTextContent("Malicious");
            expect(badge).toHaveClass("text-red-500");
        });

        it("shows Suspicious badge with yellow styling", async () => {
            mockFetchSuccess(
                createSuccessResponse({
                    payload: { reputation: "suspicious", report_count: 0 },
                }),
            );

            renderDashboard();
            await userEvent.click(screen.getByTestId("enrich-button-btc"));

            const badge = screen.getByTestId("reputation-badge-btc");
            expect(badge).toHaveTextContent("Suspicious");
            expect(badge).toHaveClass("text-yellow-500");
        });

        it("shows Clean badge with green styling", async () => {
            mockFetchSuccess(
                createSuccessResponse({
                    ioc_type: "url",
                    payload: { reputation: "clean" },
                }),
            );

            // URL IOCs are auto-enriched on mount (US-038/US-035), so we
            // wait for the reputation badge to appear rather than clicking.
            render(
                <IntelDashboard
                    iocs={[{ id: "u1", type: "url", value: "https://evil.com", is_high_value: false }]}
                    getAccessToken={mockGetAccessToken}
                />,
            );

            const badge = await screen.findByTestId("reputation-badge-url");
            expect(badge).toHaveTextContent("Clean");
            expect(badge).toHaveClass("text-green-500");
        });
    });

    describe("Success – cached indicator", () => {
        it("shows Cached badge when result came from cache", async () => {
            mockFetchSuccess(createSuccessResponse({ cached: true }));

            renderDashboard();
            await userEvent.click(screen.getByTestId("enrich-button-btc"));

            expect(screen.getByTestId("cached-badge-btc")).toBeInTheDocument();
            expect(screen.getByText("Cached")).toBeInTheDocument();
        });

        it("does NOT show Cached badge for fresh results", async () => {
            mockFetchSuccess(createSuccessResponse({ cached: false }));

            renderDashboard();
            await userEvent.click(screen.getByTestId("enrich-button-btc"));

            expect(
                screen.queryByTestId("cached-badge-btc"),
            ).not.toBeInTheDocument();
        });
    });

    describe("Success – expandable raw data", () => {
        it("shows expand toggle when payload is present", async () => {
            mockFetchSuccess(createSuccessResponse());

            renderDashboard();
            await userEvent.click(screen.getByTestId("enrich-button-btc"));

            expect(screen.getByTestId("expand-raw-btc")).toBeInTheDocument();
            expect(screen.getByText("Show raw data")).toBeInTheDocument();
        });

        it("expands and shows raw JSON data on click", async () => {
            const response = createSuccessResponse();
            mockFetchSuccess(response);

            renderDashboard();
            await userEvent.click(screen.getByTestId("enrich-button-btc"));

            // Click expand
            await userEvent.click(screen.getByTestId("expand-raw-btc"));

            const rawData = screen.getByTestId("raw-data-btc");
            expect(rawData).toBeInTheDocument();
            expect(rawData.textContent).toContain("malicious");
            expect(rawData.textContent).toContain("report_count");
            expect(screen.getByText("Hide raw data")).toBeInTheDocument();
        });

        it("collapses raw data on second click", async () => {
            mockFetchSuccess(createSuccessResponse());

            renderDashboard();
            await userEvent.click(screen.getByTestId("enrich-button-btc"));

            // Expand
            await userEvent.click(screen.getByTestId("expand-raw-btc"));
            expect(screen.getByTestId("raw-data-btc")).toBeInTheDocument();

            // Collapse
            await userEvent.click(screen.getByTestId("expand-raw-btc"));
            expect(
                screen.queryByTestId("raw-data-btc"),
            ).not.toBeInTheDocument();
        });
    });

    describe("Success – source and latency", () => {
        it("displays source name and latency", async () => {
            mockFetchSuccess(
                createSuccessResponse({ source: "btc_mempool", latency_ms: 230 }),
            );

            renderDashboard();
            await userEvent.click(screen.getByTestId("enrich-button-btc"));

            const resultSection = screen.getByTestId("enrichment-result-btc");
            expect(resultSection).toHaveTextContent("btc_mempool");
            expect(resultSection).toHaveTextContent("230ms");
        });
    });

    // ---- Error state ----

    describe("Error state", () => {
        it("shows error message and retry button on failure", async () => {
            vi.spyOn(globalThis, "fetch").mockRejectedValue(
                new Error("Connection refused"),
            );

            renderDashboard();
            await userEvent.click(screen.getByTestId("enrich-button-btc"));

            const errorEl = screen.getByTestId("enrichment-error-btc");
            expect(errorEl).toBeInTheDocument();
            expect(errorEl).toHaveTextContent("Connection refused");

            expect(screen.getByTestId("retry-button-btc")).toBeInTheDocument();
        });

        it("retry button triggers a new enrichment call", async () => {
            const fetchSpy = vi
                .spyOn(globalThis, "fetch")
                .mockRejectedValueOnce(new Error("Timeout"));

            renderDashboard();
            await userEvent.click(screen.getByTestId("enrich-button-btc"));

            // Verify error state
            expect(screen.getByTestId("enrichment-error-btc")).toBeInTheDocument();

            // Now mock success for retry
            fetchSpy.mockResolvedValueOnce({
                ok: true,
                json: () => Promise.resolve(createSuccessResponse()),
            } as Response);

            await userEvent.click(screen.getByTestId("retry-button-btc"));

            // Should now show success
            expect(
                screen.getByTestId("enrichment-result-btc"),
            ).toBeInTheDocument();
            expect(
                screen.queryByTestId("enrichment-error-btc"),
            ).not.toBeInTheDocument();
        });
    });

    // ---- Multiple IOCs ----

    describe("Multiple IOCs", () => {
        it("manages enrichment state independently per IOC", async () => {
            // First fetch (btc) succeeds, second (iban) fails
            const fetchSpy = vi.spyOn(globalThis, "fetch");
            fetchSpy.mockResolvedValueOnce({
                ok: true,
                json: () => Promise.resolve(createSuccessResponse()),
            } as Response);
            fetchSpy.mockRejectedValueOnce(new Error("Not supported"));

            renderDashboard([btcIoc, ibanIoc]);

            // Enrich BTC
            await userEvent.click(screen.getByTestId("enrich-button-btc"));
            expect(
                screen.getByTestId("enrichment-result-btc"),
            ).toBeInTheDocument();

            // Enrich IBAN (should fail)
            await userEvent.click(screen.getByTestId("enrich-button-iban"));
            expect(
                screen.getByTestId("enrichment-error-iban"),
            ).toBeInTheDocument();

            // BTC result should still be showing
            expect(
                screen.getByTestId("enrichment-result-btc"),
            ).toBeInTheDocument();
        });
    });
});
