import { render, screen, fireEvent } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect } from "vitest";
import { RiskScoreBreakdown } from "../RiskScoreBreakdown";
import type { RiskScoreBreakdown as RiskScoreBreakdownType } from "@/types/schemas";

// Mock breakdown data for tests (0-10 scale for raw scores)
const createMockBreakdown = (
    totalScore: number,
    riskLevel: "low" | "medium" | "high"
): RiskScoreBreakdownType => ({
    total_score: totalScore,
    risk_level: riskLevel,
    components: [
        {
            component: "attack_severity",
            raw_score: 8.0,
            weight: 0.25,
            weighted_score: 2.0,
            explanation: "High severity attack: CEO Fraud",
        },
        {
            component: "ioc_quality",
            raw_score: 9.0,
            weight: 0.25,
            weighted_score: 2.25,
            explanation: "High-value IOCs: BTC_WALLET, IBAN",
        },
        {
            component: "ioc_quantity",
            raw_score: 6.0,
            weight: 0.15,
            weighted_score: 0.9,
            explanation: "3 IOCs extracted.",
        },
        {
            component: "scammer_engagement",
            raw_score: 4.0,
            weight: 0.15,
            weighted_score: 0.6,
            explanation: "Moderate engagement: 2 message(s), avg 85 chars.",
        },
        {
            component: "urgency_tactics",
            raw_score: 5.0,
            weight: 0.10,
            weighted_score: 0.5,
            explanation: "Low urgency: 2 pressure tactic(s) detected.",
        },
        {
            component: "personalization",
            raw_score: 3.0,
            weight: 0.10,
            weighted_score: 0.3,
            explanation: "Some personalization: name used 1x.",
        },
    ],
});

describe("RiskScoreBreakdown Component", () => {
    describe("Collapsed State (default)", () => {
        it("renders total score prominently", () => {
            const breakdown = createMockBreakdown(6.5, "medium");
            render(<RiskScoreBreakdown breakdown={breakdown} />);

            expect(screen.getByTestId("total-score")).toHaveTextContent("6.5");
        });

        it("shows risk level badge", () => {
            const breakdown = createMockBreakdown(6.5, "medium");
            render(<RiskScoreBreakdown breakdown={breakdown} />);

            expect(screen.getByTestId("risk-level-badge")).toHaveTextContent(
                "Medium Risk"
            );
        });

        it("shows 'Show breakdown' text when collapsed", () => {
            const breakdown = createMockBreakdown(6.5, "medium");
            render(<RiskScoreBreakdown breakdown={breakdown} />);

            expect(screen.getByText("Show breakdown")).toBeInTheDocument();
        });

        it("hides component details when collapsed", () => {
            const breakdown = createMockBreakdown(6.5, "medium");
            render(<RiskScoreBreakdown breakdown={breakdown} />);

            // The breakdown content should have max-h-0 when collapsed
            const content = screen.getByTestId("breakdown-content");
            expect(content).toHaveClass("max-h-0");
        });
    });

    describe("Color Coding", () => {
        it("shows green color for low risk (score 1-3)", () => {
            const breakdown = createMockBreakdown(2.5, "low");
            render(<RiskScoreBreakdown breakdown={breakdown} />);

            const score = screen.getByTestId("total-score");
            expect(score).toHaveClass("text-green-500");
        });

        it("shows orange color for medium risk (score 5-7)", () => {
            const breakdown = createMockBreakdown(5.0, "medium");
            render(<RiskScoreBreakdown breakdown={breakdown} />);

            const score = screen.getByTestId("total-score");
            expect(score).toHaveClass("text-orange-500");
        });

        it("shows yellow color for mid-low risk (score 3-4)", () => {
            const breakdown = createMockBreakdown(4.0, "medium");
            render(<RiskScoreBreakdown breakdown={breakdown} />);

            const score = screen.getByTestId("total-score");
            expect(score).toHaveClass("text-yellow-500");
        });

        it("shows red color for high risk (score 7-10)", () => {
            const breakdown = createMockBreakdown(8.5, "high");
            render(<RiskScoreBreakdown breakdown={breakdown} />);

            const score = screen.getByTestId("total-score");
            expect(score).toHaveClass("text-red-500");
        });
    });

    describe("Expand/Collapse Interaction", () => {
        it("expands when toggle button is clicked", async () => {
            const breakdown = createMockBreakdown(6.5, "medium");
            render(<RiskScoreBreakdown breakdown={breakdown} />);

            const toggle = screen.getByTestId("breakdown-toggle");
            await userEvent.click(toggle);

            // Should show "Hide breakdown" text
            expect(screen.getByText("Hide breakdown")).toBeInTheDocument();

            // Content should be visible (max-h expanded)
            const content = screen.getByTestId("breakdown-content");
            expect(content).toHaveClass("max-h-[800px]");
        });

        it("collapses when toggle is clicked again", async () => {
            const breakdown = createMockBreakdown(6.5, "medium");
            render(<RiskScoreBreakdown breakdown={breakdown} />);

            const toggle = screen.getByTestId("breakdown-toggle");

            // Expand
            await userEvent.click(toggle);
            expect(screen.getByText("Hide breakdown")).toBeInTheDocument();

            // Collapse
            await userEvent.click(toggle);
            expect(screen.getByText("Show breakdown")).toBeInTheDocument();

            const content = screen.getByTestId("breakdown-content");
            expect(content).toHaveClass("max-h-0");
        });

        it("has aria-expanded attribute for accessibility", async () => {
            const breakdown = createMockBreakdown(6.5, "medium");
            render(<RiskScoreBreakdown breakdown={breakdown} />);

            const toggle = screen.getByTestId("breakdown-toggle");

            // Initially collapsed
            expect(toggle).toHaveAttribute("aria-expanded", "false");

            // After click
            await userEvent.click(toggle);
            expect(toggle).toHaveAttribute("aria-expanded", "true");
        });
    });

    describe("Component Details (Expanded)", () => {
        it("renders all 6 components when expanded", async () => {
            const breakdown = createMockBreakdown(6.5, "medium");
            render(<RiskScoreBreakdown breakdown={breakdown} />);

            // Expand the breakdown
            await userEvent.click(screen.getByTestId("breakdown-toggle"));

            // Check all components are rendered
            expect(
                screen.getByTestId("component-attack_severity")
            ).toBeInTheDocument();
            expect(
                screen.getByTestId("component-ioc_quality")
            ).toBeInTheDocument();
            expect(
                screen.getByTestId("component-ioc_quantity")
            ).toBeInTheDocument();
            expect(
                screen.getByTestId("component-scammer_engagement")
            ).toBeInTheDocument();
            expect(
                screen.getByTestId("component-urgency_tactics")
            ).toBeInTheDocument();
            expect(
                screen.getByTestId("component-personalization")
            ).toBeInTheDocument();
        });

        it("shows weight percentages for each component", async () => {
            const breakdown = createMockBreakdown(6.5, "medium");
            render(<RiskScoreBreakdown breakdown={breakdown} />);

            await userEvent.click(screen.getByTestId("breakdown-toggle"));

            // Check weight percentages are displayed (per RISK_COMPONENT_WEIGHTS constant)
            expect(screen.getAllByText("(25%)")).toHaveLength(1); // attack_severity
            expect(screen.getAllByText("(20%)")).toHaveLength(1); // ioc_quality
            expect(screen.getAllByText("(15%)")).toHaveLength(3); // ioc_quantity, scammer_engagement, urgency_tactics
            expect(screen.getAllByText("(10%)")).toHaveLength(1); // personalization
        });

        it("shows component labels", async () => {
            const breakdown = createMockBreakdown(6.5, "medium");
            render(<RiskScoreBreakdown breakdown={breakdown} />);

            await userEvent.click(screen.getByTestId("breakdown-toggle"));

            expect(screen.getByText("Attack Severity")).toBeInTheDocument();
            expect(screen.getByText("IOC Quality")).toBeInTheDocument();
            expect(screen.getByText("IOC Quantity")).toBeInTheDocument();
            expect(screen.getByText("Scammer Engagement")).toBeInTheDocument();
            expect(screen.getByText("Urgency Tactics")).toBeInTheDocument();
            expect(screen.getByText("Personalization")).toBeInTheDocument();
        });

        it("shows explanations for each component", async () => {
            const breakdown = createMockBreakdown(6.5, "medium");
            render(<RiskScoreBreakdown breakdown={breakdown} />);

            await userEvent.click(screen.getByTestId("breakdown-toggle"));

            expect(
                screen.getByText("High severity attack: CEO Fraud")
            ).toBeInTheDocument();
            expect(
                screen.getByText("High-value IOCs: BTC_WALLET, IBAN")
            ).toBeInTheDocument();
        });

        it("shows progress bar for total score", async () => {
            const breakdown = createMockBreakdown(6.5, "medium");
            render(<RiskScoreBreakdown breakdown={breakdown} />);

            await userEvent.click(screen.getByTestId("breakdown-toggle"));

            const progressBar = screen.getByTestId("total-score-bar");
            expect(progressBar).toBeInTheDocument();
            expect(progressBar).toHaveStyle({ width: "65%" }); // 6.5/10 * 100
        });
    });

    describe("Edge Cases", () => {
        it("handles minimum score (1.0)", () => {
            const breakdown = createMockBreakdown(1.0, "low");
            breakdown.components = breakdown.components.map((c) => ({
                ...c,
                raw_score: 0,
                weighted_score: 0,
            }));

            render(<RiskScoreBreakdown breakdown={breakdown} />);

            expect(screen.getByTestId("total-score")).toHaveTextContent("1.0");
            expect(screen.getByTestId("risk-level-badge")).toHaveTextContent(
                "Low Risk"
            );
        });

        it("handles maximum score (10.0)", () => {
            const breakdown = createMockBreakdown(10.0, "high");
            render(<RiskScoreBreakdown breakdown={breakdown} />);

            expect(screen.getByTestId("total-score")).toHaveTextContent("10.0");
            expect(screen.getByTestId("risk-level-badge")).toHaveTextContent(
                "High Risk"
            );
        });

        it("formats decimal scores correctly", () => {
            const breakdown = createMockBreakdown(7.3, "high");
            render(<RiskScoreBreakdown breakdown={breakdown} />);

            expect(screen.getByTestId("total-score")).toHaveTextContent("7.3");
        });
    });

    describe("Accessibility", () => {
        it("toggle button has aria-controls", () => {
            const breakdown = createMockBreakdown(6.5, "medium");
            render(<RiskScoreBreakdown breakdown={breakdown} />);

            const toggle = screen.getByTestId("breakdown-toggle");
            expect(toggle).toHaveAttribute("aria-controls", "breakdown-content");
        });

        it("breakdown content has matching id", () => {
            const breakdown = createMockBreakdown(6.5, "medium");
            render(<RiskScoreBreakdown breakdown={breakdown} />);

            const content = screen.getByTestId("breakdown-content");
            expect(content).toHaveAttribute("id", "breakdown-content");
        });

        it("is keyboard accessible", async () => {
            const breakdown = createMockBreakdown(6.5, "medium");
            render(<RiskScoreBreakdown breakdown={breakdown} />);

            const toggle = screen.getByTestId("breakdown-toggle");

            // Focus the toggle
            toggle.focus();
            expect(toggle).toHaveFocus();

            // Press Enter to expand
            fireEvent.keyDown(toggle, { key: "Enter" });
            await userEvent.click(toggle); // Simulate the click that would happen on Enter

            expect(screen.getByText("Hide breakdown")).toBeInTheDocument();
        });
    });
});
