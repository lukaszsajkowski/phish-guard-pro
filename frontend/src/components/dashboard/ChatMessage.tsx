"use client";

import { useState } from "react";
import { Copy, Check, Bot, User } from "lucide-react";
import { ChatMessage as ChatMessageType } from "@/types/schemas";
import { cn } from "@/lib/utils";

interface ChatMessageProps {
    message: ChatMessageType;
    showThinking?: boolean;
}

export function ChatMessage({ message, showThinking = false }: ChatMessageProps) {
    const [copied, setCopied] = useState(false);

    const handleCopy = async () => {
        try {
            await navigator.clipboard.writeText(message.content);
            setCopied(true);
            setTimeout(() => setCopied(false), 2000);
        } catch (error) {
            console.error("Failed to copy:", error);
        }
    };

    const isBot = message.sender === "bot";

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
                {showThinking && message.thinking && (
                    <details className="mt-3 text-sm">
                        <summary className="cursor-pointer text-muted-foreground hover:text-foreground transition-colors">
                            Agent Thinking
                        </summary>
                        <div className="mt-2 pl-4 border-l-2 border-primary/20 space-y-1">
                            <p>
                                <span className="text-muted-foreground">Goal:</span>{" "}
                                {message.thinking.turn_goal}
                            </p>
                            <p>
                                <span className="text-muted-foreground">Tactic:</span>{" "}
                                {message.thinking.selected_tactic}
                            </p>
                            <p>
                                <span className="text-muted-foreground">Reasoning:</span>{" "}
                                {message.thinking.reasoning}
                            </p>
                        </div>
                    </details>
                )}

                {/* Copy button for bot messages */}
                {isBot && (
                    <button
                        onClick={handleCopy}
                        className="mt-3 inline-flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground transition-colors"
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
                )}
            </div>
        </div>
    );
}
