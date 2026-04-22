"use client";

import { useState } from "react";
import { Loader2, Send } from "lucide-react";
import { Button } from "@/components/ui/button";

interface ScammerInputProps {
    onSubmit: (message: string) => Promise<void>;
    disabled?: boolean;
}

export function ScammerInput({ onSubmit, disabled = false }: ScammerInputProps) {
    const [message, setMessage] = useState("");
    const [isSubmitting, setIsSubmitting] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const handleSubmit = async () => {
        if (!message.trim() || isSubmitting) return;

        setIsSubmitting(true);
        setError(null);

        try {
            await onSubmit(message.trim());
            setMessage(""); // Clear on success
        } catch (err) {
            setError(err instanceof Error ? err.message : "Failed to send message");
        } finally {
            setIsSubmitting(false);
        }
    };

    const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
        // Submit on Ctrl+Enter or Cmd+Enter
        if ((e.ctrlKey || e.metaKey) && e.key === "Enter") {
            e.preventDefault();
            handleSubmit();
        }
    };

    const characterCount = message.length;
    const isValid = characterCount >= 1 && characterCount <= 50000;

    return (
        <div className="space-y-3 p-4 bg-muted/30 rounded-lg border border-border/50">
            <div className="flex items-center justify-between">
                <label
                    htmlFor="scammer-input"
                    className="text-sm font-medium text-foreground"
                >
                    Paste scammer response
                </label>
                <span className="text-xs text-muted-foreground">
                    {characterCount.toLocaleString()} / 50,000
                </span>
            </div>

            <textarea
                id="scammer-input"
                data-testid="scammer-input-textarea"
                value={message}
                onChange={(e) => setMessage(e.target.value)}
                onKeyDown={handleKeyDown}
                disabled={isSubmitting || disabled}
                placeholder="Paste the scammer's reply here..."
                className="w-full min-h-[100px] p-3 rounded-md border border-input bg-background text-sm resize-y focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed"
                maxLength={50000}
            />

            {error && (
                <p className="text-sm text-destructive" data-testid="scammer-input-error">
                    {error}
                </p>
            )}

            <div className="flex items-center justify-between gap-4">
                <p className="text-xs text-muted-foreground">
                    Press <kbd className="px-1 py-0.5 rounded bg-muted text-muted-foreground font-mono text-xs">{typeof navigator !== "undefined" && /Mac/i.test(navigator.userAgent) ? "Cmd" : "Ctrl"}+Enter</kbd> to send
                </p>

                <Button
                    onClick={handleSubmit}
                    disabled={!isValid || isSubmitting || disabled}
                    className="gap-2"
                    data-testid="scammer-input-send-button"
                >
                    {isSubmitting ? (
                        <>
                            <Loader2 className="w-4 h-4 animate-spin" />
                            Sending...
                        </>
                    ) : (
                        <>
                            <Send className="w-4 h-4" />
                            Send
                        </>
                    )}
                </Button>
            </div>
        </div>
    );
}
