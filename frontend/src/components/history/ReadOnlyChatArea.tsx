"use client";

import { useState } from "react";
import { Copy, Check } from "lucide-react";
import { ChatMessage as ChatMessageType } from "@/types/schemas";

interface ReadOnlyChatAreaProps {
    messages: ChatMessageType[];
    /** Persona name to display on bot messages. Defaults to "Persona". */
    personaName?: string;
}

function ReadOnlyMessage({
    message,
    personaName,
}: {
    message: ChatMessageType;
    personaName: string;
}) {
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

    const timestamp = message.timestamp.toLocaleTimeString([], {
        hour: "2-digit",
        minute: "2-digit",
    });

    if (isBot) {
        // Persona message — left-aligned with amber avatar
        return (
            <div
                className="flex gap-2.5 items-start"
                data-testid="chat-message-bot"
            >
                {/* Amber avatar */}
                <div className="w-[26px] h-[26px] rounded-full bg-pg-amber-dim border border-pg-amber flex items-center justify-center shrink-0 mt-0.5">
                    <svg
                        width="12"
                        height="12"
                        viewBox="0 0 16 16"
                        fill="none"
                        stroke="currentColor"
                        strokeWidth="1.5"
                        className="text-pg-amber"
                    >
                        <circle cx="8" cy="5" r="3" />
                        <path d="M2 14c0-3 2.7-5 6-5s6 2 6 5" />
                    </svg>
                </div>
                <div className="flex-1 min-w-0">
                    {/* Name + time */}
                    <div className="flex items-center gap-1.5 mb-1">
                        <span className="text-[12px] font-semibold text-pg-amber">
                            {personaName}
                        </span>
                        <span className="text-[11px] text-text-muted">{timestamp}</span>
                    </div>
                    {/* Message bubble */}
                    <div className="text-[13px] text-text-secondary leading-[1.55] bg-surface2 p-[10px_12px] rounded-[0_6px_6px_6px] border border-border whitespace-pre-wrap break-words">
                        {message.content}
                    </div>

                    {/* Thinking panel (collapsed by default) */}
                    {message.thinking && (
                        <details
                            className="mt-3 group"
                            data-testid="agent-thinking-panel"
                        >
                            <summary className="flex items-center gap-2 cursor-pointer text-sm text-text-muted hover:text-text-secondary transition-colors select-none">
                                <div className="w-1 h-1 rounded-full bg-pg-accent/50 group-open:bg-pg-accent transition-colors" />
                                <span>Agent Thinking</span>
                            </summary>

                            <div className="mt-3 pl-3 border-l-2 border-border ml-0.5 space-y-3 text-sm animate-in slide-in-from-top-2 duration-200">
                                <div className="space-y-1">
                                    <span className="text-xs font-semibold text-text-muted uppercase tracking-wider">
                                        Current Goal
                                    </span>
                                    <p className="text-text-secondary leading-relaxed">
                                        {message.thinking.turn_goal}
                                    </p>
                                </div>
                                <div className="space-y-1">
                                    <span className="text-xs font-semibold text-text-muted uppercase tracking-wider">
                                        Selected Tactic
                                    </span>
                                    <div className="flex items-center gap-2 text-text-secondary">
                                        <span className="font-medium">
                                            {message.thinking.selected_tactic}
                                        </span>
                                    </div>
                                </div>
                                <div className="space-y-1">
                                    <span className="text-xs font-semibold text-text-muted uppercase tracking-wider">
                                        Reasoning
                                    </span>
                                    <p className="text-text-secondary leading-relaxed italic">
                                        &quot;{message.thinking.reasoning}&quot;
                                    </p>
                                </div>
                            </div>
                        </details>
                    )}

                    {/* Copy button */}
                    <div className="mt-2 flex items-center gap-3">
                        <button
                            onClick={handleCopy}
                            className="inline-flex items-center gap-1.5 text-xs text-text-muted hover:text-text-secondary transition-colors cursor-pointer"
                            aria-label="Copy message to clipboard"
                            data-testid="copy-response-button"
                        >
                            {copied ? (
                                <>
                                    <Check className="w-3.5 h-3.5 text-pg-green" />
                                    <span className="text-pg-green">Copied!</span>
                                </>
                            ) : (
                                <>
                                    <Copy className="w-3.5 h-3.5" />
                                    <span>Copy to clipboard</span>
                                </>
                            )}
                        </button>
                    </div>
                </div>
            </div>
        );
    }

    // Scammer message — right-aligned with accent avatar
    return (
        <div
            className="flex gap-2.5 items-start flex-row-reverse"
            data-testid="chat-message-scammer"
        >
            {/* Accent avatar */}
            <div className="w-[26px] h-[26px] rounded-full bg-pg-accent-dim border border-pg-accent flex items-center justify-center shrink-0 mt-0.5">
                <svg
                    width="12"
                    height="12"
                    viewBox="0 0 16 16"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="1.5"
                    className="text-pg-accent"
                >
                    <path d="M8 2L3 5v4c0 2.5 2 4.5 5 5 3-.5 5-2.5 5-5V5L8 2z" />
                </svg>
            </div>
            <div className="flex-1 min-w-0 text-right">
                {/* Name + time (right-aligned) */}
                <div className="flex items-center gap-1.5 mb-1 justify-end">
                    <span className="text-[11px] text-text-muted">{timestamp}</span>
                    <span className="text-[12px] font-semibold text-pg-accent">
                        Scammer
                    </span>
                </div>
                {/* Message bubble */}
                <div className="text-[13px] text-text-secondary leading-[1.55] bg-surface2 p-[10px_12px] rounded-[6px_0_6px_6px] border border-border text-left whitespace-pre-wrap break-words">
                    {message.content}
                </div>
            </div>
        </div>
    );
}

export function ReadOnlyChatArea({ messages, personaName = "Persona" }: ReadOnlyChatAreaProps) {
    // Empty state
    if (messages.length === 0) {
        return (
            <div className="flex flex-col items-center justify-center p-8 text-center bg-surface2/30 rounded-xl border border-border min-h-[200px]">
                <div className="w-16 h-16 rounded-full bg-surface2 flex items-center justify-center mb-4">
                    <svg
                        viewBox="0 0 16 16"
                        fill="none"
                        stroke="currentColor"
                        strokeWidth="1.5"
                        className="w-8 h-8 text-text-muted"
                    >
                        <rect x="2" y="3" width="12" height="10" rx="1.5" />
                        <line x1="5" y1="6.5" x2="11" y2="6.5" />
                        <line x1="5" y1="9.5" x2="8.5" y2="9.5" />
                    </svg>
                </div>
                <h3 className="text-lg font-semibold mb-2 text-text-muted">
                    No Messages
                </h3>
                <p className="text-text-muted max-w-md">
                    This session has no conversation history.
                </p>
            </div>
        );
    }

    return (
        <div className="flex flex-col" data-testid="read-only-chat-area">
            {/* Section header with horizontal rule and message count badge */}
            <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-2 flex-1 text-[11.5px] font-semibold tracking-[0.08em] uppercase text-text-muted">
                    Conversation History
                    <span className="flex-1 h-px bg-border" />
                </div>
                <span className="text-[12px] text-text-muted bg-surface2 px-2.5 py-0.5 rounded-full border border-border ml-2 shrink-0">
                    {messages.length} {messages.length === 1 ? "message" : "messages"}
                </span>
            </div>

            {/* Messages */}
            <div className="flex flex-col gap-3">
                {messages.map((message) => (
                    <ReadOnlyMessage
                        key={message.id}
                        message={message}
                        personaName={personaName}
                    />
                ))}
            </div>
        </div>
    );
}
