"use client";

import { useState } from "react";
import { Mail, Loader2, AlertTriangle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import {
    Card,
    CardContent,
    CardHeader,
    CardTitle,
    CardDescription,
    CardFooter
} from "@/components/ui/card";

// Validation constants per PRD FR-001
const MIN_CHARS = 10;
const MAX_CHARS = 50_000;

interface EmailInputProps {
    value: string;
    onChange: (value: string) => void;
    onAnalyze: (content: string) => Promise<void>;
}

export function EmailInput({ value, onChange, onAnalyze }: EmailInputProps) {
    const [isAnalyzing, setIsAnalyzing] = useState(false);

    const charCount = value.length;
    const hasContent = charCount > 0;
    const isTooShort = hasContent && charCount < MIN_CHARS;
    const isTooLong = charCount > MAX_CHARS;
    const isValidLength = charCount >= MIN_CHARS && charCount <= MAX_CHARS;
    const canAnalyze = isValidLength && !isAnalyzing;

    const getValidationMessage = (): string | null => {
        if (!hasContent) return null;
        if (isTooShort) return `Email must be at least ${MIN_CHARS} characters`;
        if (isTooLong) return `Email must not exceed ${MAX_CHARS.toLocaleString()} characters`;
        return null;
    };

    const handleAnalyze = async () => {
        if (!canAnalyze) return;

        setIsAnalyzing(true);
        try {
            await onAnalyze(value);
        } finally {
            setIsAnalyzing(false);
        }
    };

    const validationMessage = getValidationMessage();

    return (
        <div className="w-full max-w-3xl space-y-6">
            {/* Header */}
            <div className="space-y-2 text-center">
                <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-full bg-gradient-to-br from-blue-500/20 via-purple-500/20 to-pink-500/20">
                    <Mail className="h-8 w-8 text-primary" />
                </div>
                <h2 className="text-2xl font-bold tracking-tight">
                    Paste Phishing Email
                </h2>
                <p className="text-sm text-muted-foreground">
                    Paste the suspicious email content below for analysis and classification
                </p>
            </div>

            {/* Email Input Card */}
            <Card className="shadow-lg">
                <CardContent className="p-6 space-y-4">
                    <label
                        htmlFor="email-content"
                        className="sr-only"
                    >
                        Email Content
                    </label>
                    <Textarea
                        id="email-content"
                        data-testid="email-input-textarea"
                        value={value}
                        onChange={(e) => onChange(e.target.value)}
                        placeholder="Paste phishing email content here..."
                        disabled={isAnalyzing}
                        className="min-h-[300px] resize-y"
                    />

                    {/* Character counter and validation */}
                    <div className="flex items-center justify-between">
                        <span
                            id="char-counter"
                            className={`text-sm ${isTooLong
                                ? "text-destructive"
                                : "text-muted-foreground"
                                }`}
                        >
                            {charCount.toLocaleString()} / {MAX_CHARS.toLocaleString()}
                        </span>

                        {validationMessage && (
                            <div
                                id="validation-message"
                                className="flex items-center gap-2 text-sm text-amber-600 dark:text-amber-400"
                            >
                                <AlertTriangle className="h-4 w-4" />
                                <span>{validationMessage}</span>
                            </div>
                        )}
                    </div>
                </CardContent>
                <CardFooter className="px-6 pb-6 pt-0">
                    <Button
                        id="analyze-button"
                        data-testid="analyze-button"
                        onClick={handleAnalyze}
                        disabled={!canAnalyze}
                        className="w-full h-12 text-base"
                    >
                        {isAnalyzing ? (
                            <>
                                <Loader2 className="mr-2 h-5 w-5 animate-spin" />
                                Analyzing...
                            </>
                        ) : (
                            "Analyze"
                        )}
                    </Button>
                </CardFooter>
            </Card>

            {/* Helper text */}
            <p className="text-center text-xs text-muted-foreground">
                Your email content is processed locally and never stored without your consent.
            </p>
        </div>
    );
}
