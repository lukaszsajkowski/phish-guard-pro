"use client";

import { useSearchParams } from "next/navigation";
import { Shield, ArrowLeft, CheckCircle } from "lucide-react";
import Link from "next/link";
import { Suspense } from "react";

function LoginContent() {
    const searchParams = useSearchParams();
    const isJustRegistered = searchParams.get("registered") === "true";

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

                    {/* Success message for just-registered users */}
                    {isJustRegistered && (
                        <div
                            id="registration-success-message"
                            className="flex items-center gap-3 rounded-md border border-green-500/50 bg-green-500/10 p-4 text-sm text-green-600 dark:text-green-400"
                        >
                            <CheckCircle className="h-5 w-5 flex-shrink-0" />
                            <span>
                                Registration successful! You can now log in to your account.
                            </span>
                        </div>
                    )}

                    {/* Card */}
                    <div className="rounded-xl border border-border/50 bg-card p-8 shadow-xl">
                        {/* Header */}
                        <div className="mb-8 text-center">
                            <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-full bg-gradient-to-br from-blue-500/20 via-purple-500/20 to-pink-500/20">
                                <Shield className="h-7 w-7 text-primary" />
                            </div>
                            <h1 className="text-2xl font-bold tracking-tight">
                                Sign in
                            </h1>
                            <p className="mt-2 text-sm text-muted-foreground">
                                Access your PhishGuard Pro account
                            </p>
                        </div>

                        {/* Coming soon placeholder */}
                        <div className="rounded-md border border-border bg-muted/50 p-6 text-center">
                            <p className="text-sm text-muted-foreground">
                                Login functionality coming soon.
                            </p>
                            <p className="mt-2 text-xs text-muted-foreground/70">
                                This feature will be available in the next release.
                            </p>
                        </div>

                        {/* Footer */}
                        <p className="mt-6 text-center text-sm text-muted-foreground">
                            Don&apos;t have an account?{" "}
                            <Link
                                href="/register"
                                className="font-medium text-foreground underline underline-offset-4 transition-colors hover:text-primary"
                            >
                                Create one
                            </Link>
                        </p>
                    </div>
                </div>
            </main>
        </div>
    );
}

export default function LoginPage() {
    return (
        <Suspense fallback={
            <div className="flex min-h-screen items-center justify-center">
                <Shield className="h-8 w-8 animate-pulse text-primary" />
            </div>
        }>
            <LoginContent />
        </Suspense>
    );
}
