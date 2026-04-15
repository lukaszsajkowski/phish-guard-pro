"use client";

import { useState, useReducer } from "react";
import { Copy, Check, Bot, User, Pencil, X, Save, Loader2, AlertTriangle } from "lucide-react";
import { ChatMessage as ChatMessageType } from "@/types/schemas";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Alert, AlertDescription } from "@/components/ui/alert";

// Helper to get tactic icon (US-013)
function getTacticIcon(tactic: string): string {
    const tacticLower = tactic.toLowerCase();
    if (tacticLower.includes("trust")) return "🤝";
    if (tacticLower.includes("scare")) return "😨";
    if (tacticLower.includes("urgent")) return "⏰";
    if (tacticLower.includes("curious") || tacticLower.includes("question")) return "❓";
    if (tacticLower.includes("authority")) return "👮";
    if (tacticLower.includes("greed") || tacticLower.includes("offer")) return "💰";
    if (tacticLower.includes("sympathy") || tacticLower.includes("help")) return "🥺";
    return "💡"; // Default icon
}

/**
 * Edit state machine for ChatMessage
 * States: viewing -> editing -> validating -> viewing/editing (on error)
 */
export type EditMode = "viewing" | "editing" | "validating";

export interface EditState {
    mode: EditMode;
    content: string;
    error: string | null;
}

export type EditAction =
    | { type: "START_EDIT"; initialContent: string }
    | { type: "UPDATE_CONTENT"; content: string }
    | { type: "START_SAVE" }
    | { type: "SAVE_SUCCESS" }
    | { type: "SAVE_ERROR"; error: string }
    | { type: "CANCEL" };

export function editReducer(state: EditState, action: EditAction): EditState {
    switch (action.type) {
        case "START_EDIT":
            return { mode: "editing", content: action.initialContent, error: null };
        case "UPDATE_CONTENT":
            return { ...state, content: action.content };
        case "START_SAVE":
            return { ...state, mode: "validating", error: null };
        case "SAVE_SUCCESS":
            return { mode: "viewing", content: "", error: null };
        case "SAVE_ERROR":
            return { ...state, mode: "editing", error: action.error };
        case "CANCEL":
            return { mode: "viewing", content: "", error: null };
        default:
            return state;
    }
}

export const initialEditState: EditState = {
    mode: "viewing",
    content: "",
    error: null,
};

interface ChatMessageProps {
    message: ChatMessageType;
    showThinking?: boolean;
    onEditMessage?: (messageId: string, newContent: string) => Promise<void>;
    sessionId?: string;
}

export function ChatMessage({
    message,
    showThinking = false,
    onEditMessage,
    sessionId,
}: ChatMessageProps) {
    const [copied, setCopied] = useState(false);
    const [editState, dispatch] = useReducer(editReducer, initialEditState);

    // Derived state from reducer
    const isEditing = editState.mode === "editing" || editState.mode === "validating";
    const isValidating = editState.mode === "validating";
    const editedContent = editState.content;
    const validationError = editState.error;

    const handleCopy = async () => {
        const contentToCopy = isEditing ? editedContent : message.content;
        try {
            await navigator.clipboard.writeText(contentToCopy);
            setCopied(true);
            setTimeout(() => setCopied(false), 2000);
        } catch (error) {
            console.error("Failed to copy:", error);
        }
    };

    const handleEdit = () => {
        dispatch({ type: "START_EDIT", initialContent: message.content });
    };

    const handleCancel = () => {
        dispatch({ type: "CANCEL" });
    };

    const handleSave = async () => {
        if (!onEditMessage || !sessionId) {
            console.error("Edit handler or sessionId not provided");
            return;
        }

        // Check if content actually changed
        if (editedContent.trim() === message.content.trim()) {
            dispatch({ type: "CANCEL" });
            return;
        }

        dispatch({ type: "START_SAVE" });

        try {
            await onEditMessage(message.id, editedContent);
            dispatch({ type: "SAVE_SUCCESS" });
        } catch (error) {
            const errorMessage = error instanceof Error
                ? error.message
                : "Failed to save changes. Please try again.";
            dispatch({ type: "SAVE_ERROR", error: errorMessage });
        }
    };

    const isBot = message.sender === "bot";
    const canEdit = isBot && onEditMessage && sessionId;

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

                {/* Message content - edit mode or display mode */}
                {isEditing ? (
                    <div className="space-y-3">
                        <Textarea
                            value={editedContent}
                            onChange={(e) => dispatch({ type: "UPDATE_CONTENT", content: e.target.value })}
                            className="min-h-[100px] resize-y"
                            disabled={isValidating}
                            data-testid="edit-response-textarea"
                        />

                        {/* Validation error */}
                        {validationError && (
                            <Alert variant="destructive" className="py-2">
                                <AlertTriangle className="h-4 w-4" />
                                <AlertDescription className="text-sm">
                                    {validationError}
                                </AlertDescription>
                            </Alert>
                        )}

                        {/* Save/Cancel buttons */}
                        <div className="flex gap-2">
                            <Button
                                size="sm"
                                onClick={handleSave}
                                disabled={isValidating || !editedContent.trim()}
                                data-testid="save-edit-button"
                            >
                                {isValidating ? (
                                    <>
                                        <Loader2 className="w-3.5 h-3.5 mr-1.5 animate-spin" />
                                        Validating...
                                    </>
                                ) : (
                                    <>
                                        <Save className="w-3.5 h-3.5 mr-1.5" />
                                        Save
                                    </>
                                )}
                            </Button>
                            <Button
                                size="sm"
                                variant="outline"
                                onClick={handleCancel}
                                disabled={isValidating}
                                data-testid="cancel-edit-button"
                            >
                                <X className="w-3.5 h-3.5 mr-1.5" />
                                Cancel
                            </Button>
                        </div>
                    </div>
                ) : (
                    <p className="text-foreground whitespace-pre-wrap break-words">
                        {message.content}
                    </p>
                )}

                {/* Thinking panel (collapsed by default) - only show when not editing */}
                {!isEditing && showThinking && message.thinking && (
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
                                    &ldquo;{message.thinking.reasoning}&rdquo;
                                </p>
                            </div>
                        </div>
                    </details>
                )}

                {/* Action buttons for bot messages - only show when not editing */}
                {isBot && !isEditing && (
                    <div className="mt-3 flex items-center gap-3">
                        {/* Edit button */}
                        {canEdit && (
                            <button
                                onClick={handleEdit}
                                className="inline-flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring rounded-sm"
                                data-testid="edit-response-button"
                                aria-label="Edit message"
                            >
                                <Pencil className="w-3.5 h-3.5" />
                                <span>Edit</span>
                            </button>
                        )}

                        {/* Copy button */}
                        <button
                            onClick={handleCopy}
                            className="inline-flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring rounded-sm"
                            data-testid="copy-response-button"
                            aria-label="Copy message to clipboard"
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
