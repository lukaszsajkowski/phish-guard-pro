"use client";

import { MessageSquare, Copy, Check, Bot, User } from "lucide-react";
import { useState } from "react";
import { ChatMessage as ChatMessageType } from "@/types/schemas";
import { cn } from "@/lib/utils";

interface ReadOnlyChatAreaProps {
    messages: ChatMessageType[];
}

// Helper to get tactic icon (same as ChatMessage)
function getTacticIcon(tactic: string): string {
    const tacticLower = tactic.toLowerCase();
    if (tacticLower.includes("trust")) return "handshake";
    if (tacticLower.includes("scare")) return "fearful";
    if (tacticLower.includes("urgent")) return "clock";
    if (tacticLower.includes("curious") || tacticLower.includes("question")) return "question";
    if (tacticLower.includes("authority")) return "badge";
    if (tacticLower.includes("greed") || tacticLower.includes("offer")) return "money";
    if (tacticLower.includes("sympathy") || tacticLower.includes("help")) return "pleading";
    return "lightbulb"; // Default icon
}

function ReadOnlyMessage({ message }: { message: ChatMessageType }) {
    const [copied, setCopied] = useState(false);
    const isBot = message.sender === "bot";

    const handleCopy = async () => {
        try {
            await navigator.clipboard.writeText(message.content);
            setCopied(true);
            setTimeout(() => setCopied(false), 2000);
        } catch (error) {
            console.error("Failed to copy:", error);
        }
    };

    return (
        <div
            className={cn(
                "flex gap-3 p-4 rounded-lg",
                isBot
                    ? "bg-primary/5 border border-primary/10"
                    : "bg-muted/50 border border-border/50"
            )}
            data-testid={`chat-message-${message.sender}`}
        >
            {/* Avatar */}
            <div
                className={cn(
                    "flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center",
                    isBot ? "bg-primary/10" : "bg-orange-500/10"
                )}
            >
                {isBot ? (
                    <Bot className="w-4 h-4 text-primary" />
                ) : (
                    <User className="w-4 h-4 text-orange-500" />
                )}
            </div>

            {/* Content */}
            <div className="flex-1 min-w-0">
                {/* Header */}
                <div className="flex items-center justify-between mb-2">
                    <span
                        className={cn(
                            "text-sm font-medium",
                            isBot ? "text-primary" : "text-orange-500"
                        )}
                    >
                        {isBot ? "PhishGuard Bot" : "Scammer"}
                    </span>
                    <span className="text-xs text-muted-foreground">
                        {message.timestamp.toLocaleTimeString([], {
                            hour: "2-digit",
                            minute: "2-digit",
                        })}
                    </span>
                </div>

                {/* Message content */}
                <p className="text-foreground whitespace-pre-wrap break-words">
                    {message.content}
                </p>

                {/* Thinking panel (collapsed by default) */}
                {isBot && message.thinking && (
                    <details
                        className="mt-3 group"
                        data-testid="agent-thinking-panel"
                    >
                        <summary className="flex items-center gap-2 cursor-pointer text-sm text-muted-foreground hover:text-foreground transition-colors select-none">
                            <div className="w-1 h-1 rounded-full bg-primary/50 group-open:bg-primary transition-colors" />
                            <span>Agent Thinking</span>
                        </summary>

                        <div className="mt-3 pl-3 border-l-2 border-primary/10 ml-0.5 space-y-3 text-sm animate-in slide-in-from-top-2 duration-200">
                            {/* Goal */}
                            <div className="space-y-1">
                                <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                                    Current Goal
                                </span>
                                <p className="text-foreground/90 leading-relaxed">
                                    {message.thinking.turn_goal}
                                </p>
                            </div>

                            {/* Tactic */}
                            <div className="space-y-1">
                                <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                                    Selected Tactic
                                </span>
                                <div className="flex items-center gap-2 text-foreground/90">
                                    <span className="text-lg" aria-hidden="true">
                                        {getTacticIcon(message.thinking.selected_tactic)}
                                    </span>
                                    <span className="font-medium">
                                        {message.thinking.selected_tactic}
                                    </span>
                                </div>
                            </div>

                            {/* Reasoning */}
                            <div className="space-y-1">
                                <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                                    Reasoning
                                </span>
                                <p className="text-foreground/90 leading-relaxed italic">
                                    &quot;{message.thinking.reasoning}&quot;
                                </p>
                            </div>
                        </div>
                    </details>
                )}

                {/* Copy button for bot messages */}
                {isBot && (
                    <div className="mt-3 flex items-center gap-3">
                        <button
                            onClick={handleCopy}
                            className="inline-flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground transition-colors"
                            data-testid="copy-response-button"
                        >
                            {copied ? (
                                <>
                                    <Check className="w-3.5 h-3.5 text-green-500" />
                                    <span className="text-green-500">Copied!</span>
                                </>
                            ) : (
                                <>
                                    <Copy className="w-3.5 h-3.5" />
                                    <span>Copy to clipboard</span>
                                </>
                            )}
                        </button>
                    </div>
                )}
            </div>
        </div>
    );
}

export function ReadOnlyChatArea({ messages }: ReadOnlyChatAreaProps) {
    // Empty state
    if (messages.length === 0) {
        return (
            <div className="flex flex-col items-center justify-center p-8 text-center bg-gradient-to-br from-muted/30 to-muted/10 rounded-xl border border-border/50 min-h-[200px]">
                <div className="w-16 h-16 rounded-full bg-muted/50 flex items-center justify-center mb-4">
                    <MessageSquare className="w-8 h-8 text-muted-foreground" />
                </div>
                <h3 className="text-lg font-semibold mb-2 text-muted-foreground">
                    No Messages
                </h3>
                <p className="text-muted-foreground max-w-md">
                    This session has no conversation history.
                </p>
            </div>
        );
    }

    return (
        <div className="flex flex-col h-full" data-testid="read-only-chat-area">
            {/* Chat header */}
            <div className="flex items-center justify-between pb-3 border-b border-border/50 mb-4">
                <h3 className="text-lg font-semibold">Conversation History</h3>
                <span className="text-sm text-muted-foreground">
                    {messages.length} {messages.length === 1 ? "message" : "messages"}
                </span>
            </div>

            {/* Messages container */}
            <div className="flex-1 overflow-y-auto space-y-4 pr-2">
                {messages.map((message) => (
                    <ReadOnlyMessage key={message.id} message={message} />
                ))}
            </div>
        </div>
    );
}
