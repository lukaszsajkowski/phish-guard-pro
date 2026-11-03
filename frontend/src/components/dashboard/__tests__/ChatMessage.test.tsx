import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { ChatMessage } from "../ChatMessage";
import type { ChatMessage as ChatMessageType } from "@/types/schemas";

const warning = {
    message: "This reply may break the persona's role. Review it before sending.",
    confidence: 0.87,
};

const makeMessage = (overrides: Partial<ChatMessageType> = {}): ChatMessageType => ({
    id: "m1",
    sender: "bot",
    content: "Hello there",
    timestamp: new Date(0),
    ...overrides,
});

describe("ChatMessage in-role warning", () => {
    it("shows the warning with confidence on a bot message and keeps copy enabled", () => {
        render(<ChatMessage message={makeMessage({ inRoleWarning: warning })} />);
        const notice = screen.getByTestId("in-role-warning");
        expect(notice).toHaveTextContent(
            "This reply may break the persona's role. Review it before sending. (Basal, p=0.87)"
        );
        expect(notice).toHaveAttribute("role", "status");
        expect(screen.getByTestId("copy-response-button")).toBeEnabled();
    });

    it("shows nothing without a warning", () => {
        render(<ChatMessage message={makeMessage()} />);
        expect(screen.queryByTestId("in-role-warning")).not.toBeInTheDocument();
    });

    it("shows nothing when the warning is null", () => {
        render(<ChatMessage message={makeMessage({ inRoleWarning: null })} />);
        expect(screen.queryByTestId("in-role-warning")).not.toBeInTheDocument();
    });

    it("never shows on a scammer message", () => {
        render(<ChatMessage message={makeMessage({ sender: "scammer", inRoleWarning: warning })} />);
        expect(screen.queryByTestId("in-role-warning")).not.toBeInTheDocument();
    });

    it("is hidden in edit mode", () => {
        render(
            <ChatMessage
                message={makeMessage({ inRoleWarning: warning })}
                sessionId="s1"
                onEditMessage={async () => {}}
            />
        );
        expect(screen.getByTestId("in-role-warning")).toBeInTheDocument();
        fireEvent.click(screen.getByTestId("edit-response-button"));
        expect(screen.queryByTestId("in-role-warning")).not.toBeInTheDocument();
    });
});
