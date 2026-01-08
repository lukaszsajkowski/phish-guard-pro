"use client";

import { useState } from "react";
import { Shield, Eye, EyeOff, Loader2, ArrowLeft } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { createClient } from "@supabase/supabase-js";

export default function RegisterPage() {
    const router = useRouter();
    const [email, setEmail] = useState("");
    const [password, setPassword] = useState("");
    const [confirmPassword, setConfirmPassword] = useState("");
    const [showPassword, setShowPassword] = useState(false);
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const passwordMinLength = 8;
    const isPasswordValid = password.length >= passwordMinLength;
    const doPasswordsMatch = password === confirmPassword;
    const isEmailValid = /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);

    const canSubmit =
        email && password && confirmPassword && isEmailValid && isPasswordValid && doPasswordsMatch && !isLoading;

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!canSubmit) return;

        setIsLoading(true);
        setError(null);

        try {
            const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL;
            const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;

            if (!supabaseUrl || !supabaseAnonKey) {
                throw new Error("Supabase configuration missing");
            }

            const supabase = createClient(supabaseUrl, supabaseAnonKey);

            const { error: signUpError } = await supabase.auth.signUp({
                email,
                password,
            });

            if (signUpError) {
                if (signUpError.message.includes("already registered")) {
                    setError("An account with this email already exists");
                } else {
                    setError(signUpError.message);
                }
                return;
            }

            // Success - redirect to home (login page)
            router.push("/?registered=true");
        } catch {
            setError("Registration failed. Please try again.");
        } finally {
            setIsLoading(false);
        }
    };

    return (
        <div className="flex min-h-screen flex-col bg-background">
            {/* Header */}
            <header className="border-b border-border/40 bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
                <div className="container flex h-16 items-center px-4">
                    <Link href="/" className="flex items-center gap-2">
                        <Shield className="h-8 w-8 text-primary" />
                        <span className="text-xl font-bold tracking-tight">
                            PhishGuard Pro
                        </span>
                    </Link>
                </div>
            </header>

            <main className="flex flex-1 items-center justify-center px-4 py-12">
                <div className="w-full max-w-md space-y-8">
                    {/* Back to home */}
                    <Link
                        href="/"
                        className="inline-flex items-center gap-2 text-sm text-muted-foreground transition-colors hover:text-foreground"
                    >
                        <ArrowLeft className="h-4 w-4" />
                        Back to home
                    </Link>

                    {/* Card */}
                    <div className="rounded-xl border border-border/50 bg-card p-8 shadow-xl">
                        {/* Header */}
                        <div className="mb-8 text-center">
                            <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-full bg-gradient-to-br from-blue-500/20 via-purple-500/20 to-pink-500/20">
                                <Shield className="h-7 w-7 text-primary" />
                            </div>
                            <h1 className="text-2xl font-bold tracking-tight">
                                Create an account
                            </h1>
                            <p className="mt-2 text-sm text-muted-foreground">
                                Start analyzing phishing threats today
                            </p>
                        </div>

                        {/* Form */}
                        <form onSubmit={handleSubmit} className="space-y-6">
                            {/* Error message */}
                            {error && (
                                <div
                                    id="register-error"
                                    className="rounded-md border border-destructive/50 bg-destructive/10 p-3 text-sm text-destructive"
                                >
                                    {error}
                                </div>
                            )}

                            {/* Email field */}
                            <div className="space-y-2">
                                <label
                                    htmlFor="email"
                                    className="text-sm font-medium leading-none"
                                >
                                    Email
                                </label>
                                <input
                                    id="email"
                                    type="email"
                                    placeholder="you@example.com"
                                    value={email}
                                    onChange={(e) => setEmail(e.target.value)}
                                    className="flex h-11 w-full rounded-md border border-input bg-background px-4 py-2 text-sm transition-colors placeholder:text-muted-foreground focus:border-ring focus:outline-none focus:ring-2 focus:ring-ring/20 disabled:cursor-not-allowed disabled:opacity-50"
                                    autoComplete="email"
                                    disabled={isLoading}
                                />
                                {email && !isEmailValid && (
                                    <p className="text-xs text-destructive">
                                        Please enter a valid email address
                                    </p>
                                )}
                            </div>

                            {/* Password field */}
                            <div className="space-y-2">
                                <label
                                    htmlFor="password"
                                    className="text-sm font-medium leading-none"
                                >
                                    Password
                                </label>
                                <div className="relative">
                                    <input
                                        id="password"
                                        type={showPassword ? "text" : "password"}
                                        placeholder="••••••••"
                                        value={password}
                                        onChange={(e) => setPassword(e.target.value)}
                                        className="flex h-11 w-full rounded-md border border-input bg-background px-4 py-2 pr-10 text-sm transition-colors placeholder:text-muted-foreground focus:border-ring focus:outline-none focus:ring-2 focus:ring-ring/20 disabled:cursor-not-allowed disabled:opacity-50"
                                        autoComplete="new-password"
                                        disabled={isLoading}
                                    />
                                    <button
                                        type="button"
                                        onClick={() => setShowPassword(!showPassword)}
                                        className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                                        tabIndex={-1}
                                    >
                                        {showPassword ? (
                                            <EyeOff className="h-4 w-4" />
                                        ) : (
                                            <Eye className="h-4 w-4" />
                                        )}
                                    </button>
                                </div>
                                {password && !isPasswordValid && (
                                    <p className="text-xs text-destructive">
                                        Password must be at least {passwordMinLength} characters
                                    </p>
                                )}
                            </div>

                            {/* Confirm Password field */}
                            <div className="space-y-2">
                                <label
                                    htmlFor="confirm-password"
                                    className="text-sm font-medium leading-none"
                                >
                                    Confirm Password
                                </label>
                                <input
                                    id="confirm-password"
                                    type={showPassword ? "text" : "password"}
                                    placeholder="••••••••"
                                    value={confirmPassword}
                                    onChange={(e) => setConfirmPassword(e.target.value)}
                                    className="flex h-11 w-full rounded-md border border-input bg-background px-4 py-2 text-sm transition-colors placeholder:text-muted-foreground focus:border-ring focus:outline-none focus:ring-2 focus:ring-ring/20 disabled:cursor-not-allowed disabled:opacity-50"
                                    autoComplete="new-password"
                                    disabled={isLoading}
                                />
                                {confirmPassword && !doPasswordsMatch && (
                                    <p className="text-xs text-destructive">
                                        Passwords do not match
                                    </p>
                                )}
                            </div>

                            {/* Submit button */}
                            <button
                                id="register-button"
                                type="submit"
                                disabled={!canSubmit}
                                className="inline-flex h-11 w-full items-center justify-center gap-2 rounded-md bg-primary text-sm font-medium text-primary-foreground transition-colors hover:bg-primary/90 disabled:pointer-events-none disabled:opacity-50"
                            >
                                {isLoading ? (
                                    <>
                                        <Loader2 className="h-4 w-4 animate-spin" />
                                        Creating account...
                                    </>
                                ) : (
                                    "Create account"
                                )}
                            </button>
                        </form>

                        {/* Footer */}
                        <p className="mt-6 text-center text-sm text-muted-foreground">
                            Already have an account?{" "}
                            <Link
                                href="/"
                                className="font-medium text-foreground underline underline-offset-4 transition-colors hover:text-primary"
                            >
                                Sign in
                            </Link>
                        </p>
                    </div>

                    {/* Security notice */}
                    <p className="text-center text-xs text-muted-foreground">
                        Your data is encrypted and never shared with third parties.
                    </p>
                </div>
            </main>
        </div>
    );
}
