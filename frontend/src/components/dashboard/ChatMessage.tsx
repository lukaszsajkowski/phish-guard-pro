"use client";

import { useState } from "react";
import { Copy, Check, Bot, User, Pencil, X, Save, Loader2, AlertTriangle } from "lucide-react";
import { ChatMessage as ChatMessageType } from "@/types/schemas";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Alert, AlertDescription } from "@/components/ui/alert";

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
    const [isEditing, setIsEditing] = useState(false);
    const [editedContent, setEditedContent] = useState(message.content);
    const [isValidating, setIsValidating] = useState(false);
    const [validationError, setValidationError] = useState<string | null>(null);

    const handleCopy = async () => {
        // Copy the current content (edited or original)
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
        setIsEditing(true);
        setEditedContent(message.content);
        setValidationError(null);
    };

    const handleCancel = () => {
        setIsEditing(false);
        setEditedContent(message.content);
        setValidationError(null);
    };

    const handleSave = async () => {
        if (!onEditMessage || !sessionId) {
            console.error("Edit handler or sessionId not provided");
            return;
        }

        // Check if content actually changed
        if (editedContent.trim() === message.content.trim()) {
            setIsEditing(false);
            return;
        }

        setIsValidating(true);
        setValidationError(null);

        try {
            await onEditMessage(message.id, editedContent);
            setIsEditing(false);
        } catch (error) {
            if (error instanceof Error) {
                setValidationError(error.message);
            } else {
                setValidationError("Failed to save changes. Please try again.");
            }
        } finally {
            setIsValidating(false);
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
                            onChange={(e) => setEditedContent(e.target.value)}
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

                {/* Action buttons for bot messages - only show when not editing */}
                {isBot && !isEditing && (
                    <div className="mt-3 flex items-center gap-3">
                        {/* Edit button */}
                        {canEdit && (
                            <button
                                onClick={handleEdit}
                                className="inline-flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground transition-colors"
                                data-testid="edit-response-button"
                            >
                                <Pencil className="w-3.5 h-3.5" />
                                <span>Edit</span>
                            </button>
                        )}

                        {/* Copy button */}
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
