"use client";

import { useRef, useEffect } from "react";
import { Loader2, MessageSquare, Sparkles } from "lucide-react";
import { ChatMessage as ChatMessageType } from "@/types/schemas";
import { ChatMessage } from "./ChatMessage";
import { Button } from "@/components/ui/button";

interface ChatAreaProps {
    messages: ChatMessageType[];
    isGenerating: boolean;
    onGenerateResponse: () => void;
    showGenerateButton: boolean;
}

export function ChatArea({
    messages,
    isGenerating,
    onGenerateResponse,
    showGenerateButton,
}: ChatAreaProps) {
    const messagesEndRef = useRef<HTMLDivElement>(null);

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
                <span className="text-sm text-muted-foreground">
                    Turn {Math.ceil(messages.length / 2)}/20
                </span>
            </div>

            {/* Messages container */}
            <div className="flex-1 overflow-y-auto space-y-4 pr-2">
                {messages.map((message) => (
                    <ChatMessage
                        key={message.id}
                        message={message}
                        showThinking={message.sender === "bot"}
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

            {/* Generate button for subsequent turns (will be implemented in US-010) */}
            {messages.length > 0 && showGenerateButton && !isGenerating && (
                <div className="pt-4 border-t border-border/50 mt-4">
                    <Button
                        onClick={onGenerateResponse}
                        className="w-full gap-2"
                        data-testid="generate-next-response-button"
                    >
                        <Sparkles className="w-4 h-4" />
                        Generate Next Response
                    </Button>
                </div>
            )}
        </div>
    );
}
