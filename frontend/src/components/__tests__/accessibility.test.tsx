import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi, describe, it, expect, beforeEach } from "vitest";
import { ChatMessage } from "../dashboard/ChatMessage";
import { IntelDashboard } from "../dashboard/IntelDashboard";
import { RiskScoreBreakdown } from "../dashboard/RiskScoreBreakdown";
import { ReadOnlyChatArea } from "../history/ReadOnlyChatArea";
import { PhishingEmailCard } from "../history/PhishingEmailCard";
import { ThemeToggle } from "../app/ThemeToggle";
import { ThemeProvider } from "../theme-provider";
import type {
    ChatMessage as ChatMessageType,
    ExtractedIOC,
    RiskScoreBreakdown as RiskScoreBreakdownType,
} from "@/types/schemas";

const botMessage: ChatMessageType = {
    id: "m1",
    sender: "bot",
    content: "Hello there",
    timestamp: new Date(0),
};

const ibanIoc: ExtractedIOC = {
    id: "ioc-1",
    type: "iban",
    value: "DE89370400440532013000",
    is_high_value: false,
};

const breakdown: RiskScoreBreakdownType = {
    total_score: 5,
    risk_level: "medium",
    components: [],
};

beforeEach(() => {
    Object.assign(navigator, {
        clipboard: { writeText: vi.fn().mockResolvedValue(undefined) },
    });
});

describe("copy buttons announce their state", () => {
    it("ChatMessage copy button is a polite live region named by its state", async () => {
        render(<ChatMessage message={botMessage} />);
        const button = screen.getByTestId("copy-response-button");
        expect(button).toHaveAttribute("aria-live", "polite");
        expect(button).toHaveAccessibleName("Copy to clipboard");
        fireEvent.click(button);
        await waitFor(() => expect(button).toHaveAccessibleName("Copied!"));
    });

    it("ReadOnlyChatArea copy button name changes to Copied! after click", async () => {
        render(<ReadOnlyChatArea messages={[botMessage]} />);
        const button = screen.getByTestId("copy-response-button");
        expect(button).toHaveAttribute("aria-live", "polite");
        expect(button).toHaveAccessibleName("Copy to clipboard");
        fireEvent.click(button);
        await waitFor(() => expect(button).toHaveAccessibleName("Copied!"));
    });

    it("IntelDashboard IOC copy button uses a tooltip instead of title and announces Copied!", async () => {
        render(<IntelDashboard iocs={[ibanIoc]} />);
        const button = screen.getByRole("button", { name: "Copy IOC value" });
        expect(button).not.toHaveAttribute("title");
        expect(button).toHaveAttribute("aria-live", "polite");
        fireEvent.click(button);
        await waitFor(() => expect(button).toHaveAccessibleName("Copied!"));
    });
});

describe("expandable sections expose their state", () => {
    it("PhishingEmailCard toggle reports aria-expanded and controls the body", async () => {
        const longEmail = ["One", "Two", "Three", "Four", "Five"].join("\n\n");
        render(<PhishingEmailCard emailContent={longEmail} />);
        const toggle = screen.getByTestId("email-expand-toggle");
        expect(toggle).toHaveAttribute("aria-expanded", "false");
        expect(toggle).toHaveAttribute("aria-controls", screen.getByTestId("email-body").id);
        expect(screen.getByTestId("email-body").id).not.toBe("");
        fireEvent.click(toggle);
        expect(toggle).toHaveAttribute("aria-expanded", "true");
    });

    it("two RiskScoreBreakdowns on one page control distinct content ids", () => {
        render(
            <>
                <RiskScoreBreakdown breakdown={breakdown} />
                <RiskScoreBreakdown breakdown={breakdown} />
            </>,
        );
        const contents = screen.getAllByTestId("breakdown-content");
        const ids = contents.map((el) => el.id);
        expect(new Set(ids).size).toBe(2);
        const controlled = Array.from(document.querySelectorAll("[aria-controls]")).map((el) =>
            el.getAttribute("aria-controls"),
        );
        for (const id of ids) expect(controlled).toContain(id);
    });
});

describe("icon-only buttons have tooltips", () => {
    it("ThemeToggle shows its action in a tooltip on keyboard focus", async () => {
        const user = userEvent.setup();
        render(
            <ThemeProvider>
                <ThemeToggle />
            </ThemeProvider>,
        );
        await user.tab();
        expect(await screen.findByRole("tooltip")).toHaveTextContent("Switch to dark mode");
    });
});
