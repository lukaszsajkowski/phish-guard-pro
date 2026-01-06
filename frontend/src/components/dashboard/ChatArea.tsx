"use client";

import { useRef, useEffect } from "react";
import { Loader2, MessageSquare, Sparkles } from "lucide-react";
import { ChatMessage as ChatMessageType } from "@/types/schemas";
import { ChatMessage } from "./ChatMessage";
import { ScammerInput } from "./ScammerInput";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

interface ChatAreaProps {
    messages: ChatMessageType[];
    isGenerating: boolean;
    onGenerateResponse: () => void;
    showGenerateButton: boolean;
    onEditMessage?: (messageId: string, newContent: string) => Promise<void>;
    onSubmitScammerMessage?: (message: string) => Promise<void>;
    sessionId?: string;
    turnCount?: number;
    turnLimit?: number;
}

/**
 * Get the turn counter color based on current turn (US-015, US-027)
 * - Default: turns 1-14
 * - Yellow: turns 15-19
 * - Red: turns 20+
 */
function getTurnCounterColor(turnCount: number): string {
    if (turnCount >= 20) return "text-red-500";
    if (turnCount >= 15) return "text-yellow-500";
    return "text-muted-foreground";
}

/**
 * Format the turn counter display (US-027)
 * - "Turn X/20" for turns 1-20
 * - "Turn X/20+" for turns > 20
 */
function formatTurnCounter(turnCount: number, turnLimit: number): string {
    if (turnCount > 20) {
        return `Turn ${turnCount}/20+`;
    }
    return `Turn ${turnCount}/${turnLimit}`;
}

export function ChatArea({
    messages,
    isGenerating,
    onGenerateResponse,
    showGenerateButton,
    onEditMessage,
    onSubmitScammerMessage,
    sessionId,
    turnCount,
    turnLimit = 20,
}: ChatAreaProps) {
    const messagesEndRef = useRef<HTMLDivElement>(null);

    // Calculate turn count from messages if not provided
    const effectiveTurnCount = turnCount ?? (
        messages.filter((m) => m.sender === "bot").length || 1
    );

    // Auto-scroll to bottom when new messages arrive
    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    }, [messages]);

    // Empty state with generate button
    if (messages.length === 0 && showGenerateButton) {
        return (
            <div className="flex flex-col items-center justify-center p-8 text-center bg-gradient-to-br from-muted/30 to-muted/10 rounded-xl border border-border/50 min-h-[300px]">
                <div className="w-16 h-16 rounded-full bg-primary/10 flex items-center justify-center mb-4">
                    <MessageSquare className="w-8 h-8 text-primary" />
                </div>
                <h3 className="text-lg font-semibold mb-2">Ready to Engage</h3>
                <p className="text-muted-foreground mb-6 max-w-md">
                    Generate your first response to the phishing email. The AI will craft a
                    believable reply in the selected persona's style.
                </p>
                <Button
                    onClick={onGenerateResponse}
                    disabled={isGenerating}
                    size="lg"
                    className="gap-2"
                    data-testid="generate-response-button"
                >
                    {isGenerating ? (
                        <>
                            <Loader2 className="w-4 h-4 animate-spin" />
                            Generating...
                        </>
                    ) : (
                        <>
                            <Sparkles className="w-4 h-4" />
                            Generate Response
                        </>
                    )}
                </Button>
            </div>
        );
    }

    return (
        <div className="flex flex-col h-full">
            {/* Chat header */}
            <div className="flex items-center justify-between pb-3 border-b border-border/50 mb-4">
                <h3 className="text-lg font-semibold">Conversation</h3>
                <span
                    className={cn(
                        "text-sm font-medium px-2 py-0.5 rounded",
                        getTurnCounterColor(effectiveTurnCount),
                        effectiveTurnCount >= 15 && "bg-current/10"
                    )}
                    data-testid="turn-counter"
                >
                    {formatTurnCounter(effectiveTurnCount, turnLimit)}
                </span>
            </div>

            {/* Messages container */}
            <div className="flex-1 overflow-y-auto space-y-4 pr-2">
                {messages.map((message) => (
                    <ChatMessage
                        key={message.id}
                        message={message}
                        showThinking={message.sender === "bot"}
                        onEditMessage={onEditMessage}
                        sessionId={sessionId}
                    />
                ))}

                {/* Loading state for generation */}
                {isGenerating && (
                    <div className="flex items-center gap-2 p-4 bg-primary/5 rounded-lg border border-primary/10 animate-pulse">
                        <Loader2 className="w-4 h-4 animate-spin text-primary" />
                        <span className="text-sm text-muted-foreground">
                            Generating response...
                        </span>
                    </div>
                )}

                <div ref={messagesEndRef} />
            </div>

            {/* Scammer input - shown after last bot message when not generating */}
            {messages.length > 0 &&
                messages[messages.length - 1]?.sender === "bot" &&
                !isGenerating &&
                onSubmitScammerMessage && (
                    <div className="pt-4 border-t border-border/50 mt-4">
                        <ScammerInput
                            onSubmit={onSubmitScammerMessage}
                            disabled={isGenerating}
                        />
                    </div>
                )}
        </div>
    );
}

