"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Shield, LogOut, Loader2, AlertTriangle } from "lucide-react";
import Link from "next/link";
import { createClient, User } from "@supabase/supabase-js";

export default function DashboardPage() {
    const router = useRouter();
    const [user, setUser] = useState<User | null>(null);
    const [isLoading, setIsLoading] = useState(true);
    const [isSigningOut, setIsSigningOut] = useState(false);

    useEffect(() => {
        const checkAuth = async () => {
            const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL;
            const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;

            if (!supabaseUrl || !supabaseAnonKey) {
                router.push("/login");
                return;
            }

            const supabase = createClient(supabaseUrl, supabaseAnonKey);
            const { data: { user } } = await supabase.auth.getUser();

            if (!user) {
                router.push("/login");
                return;
            }

            setUser(user);
            setIsLoading(false);
        };

        checkAuth();
    }, [router]);

    const handleSignOut = async () => {
        setIsSigningOut(true);

        try {
            const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL;
            const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;

            if (!supabaseUrl || !supabaseAnonKey) {
                throw new Error("Supabase configuration missing");
            }

            const supabase = createClient(supabaseUrl, supabaseAnonKey);
            await supabase.auth.signOut();
            router.push("/login");
        } catch {
            setIsSigningOut(false);
        }
    };

    if (isLoading) {
        return (
            <div className="flex min-h-screen items-center justify-center bg-background">
                <div className="flex items-center gap-3">
                    <Loader2 className="h-6 w-6 animate-spin text-primary" />
                    <span className="text-muted-foreground">Loading...</span>
                </div>
            </div>
        );
    }

    return (
        <div className="flex min-h-screen flex-col bg-background">
            {/* Header */}
            <header className="border-b border-border/40 bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
                <div className="container flex h-16 items-center justify-between px-4">
                    <Link href="/dashboard" className="flex items-center gap-2">
                        <Shield className="h-8 w-8 text-primary" />
                        <span className="text-xl font-bold tracking-tight">
                            PhishGuard Pro
                        </span>
                    </Link>
                    <button
                        id="signout-button"
                        onClick={handleSignOut}
                        disabled={isSigningOut}
                        className="inline-flex items-center gap-2 rounded-md border border-border bg-background px-4 py-2 text-sm font-medium transition-colors hover:bg-muted disabled:pointer-events-none disabled:opacity-50"
                    >
                        {isSigningOut ? (
                            <>
                                <Loader2 className="h-4 w-4 animate-spin" />
                                Signing out...
                            </>
                        ) : (
                            <>
                                <LogOut className="h-4 w-4" />
                                Sign out
                            </>
                        )}
                    </button>
                </div>
            </header>

            {/* Main content */}
            <main className="flex flex-1 flex-col items-center justify-center px-4 py-12">
                <div className="w-full max-w-2xl space-y-8 text-center">
                    {/* Welcome section */}
                    <div className="space-y-4">
                        <div className="mx-auto flex h-20 w-20 items-center justify-center rounded-full bg-gradient-to-br from-blue-500/20 via-purple-500/20 to-pink-500/20">
                            <Shield className="h-10 w-10 text-primary" />
                        </div>
                        <h1 className="text-3xl font-bold tracking-tight">
                            Welcome to PhishGuard Pro
                        </h1>
                        <p className="text-lg text-muted-foreground">
                            Signed in as{" "}
                            <span id="user-email" className="font-medium text-foreground">
                                {user?.email}
                            </span>
                        </p>
                    </div>

                    {/* Coming soon placeholder */}
                    <div className="rounded-xl border border-border/50 bg-card p-8 shadow-lg">
                        <div className="flex items-center justify-center gap-3 text-amber-600 dark:text-amber-400">
                            <AlertTriangle className="h-6 w-6" />
                            <h2 className="text-lg font-semibold">Dashboard Under Construction</h2>
                        </div>
                        <p className="mt-4 text-muted-foreground">
                            The phishing analysis dashboard is being developed. Soon you&apos;ll be able to
                            paste suspicious emails, analyze threats, and generate intelligent responses.
                        </p>
                        <div className="mt-6 flex flex-wrap justify-center gap-4 text-sm text-muted-foreground">
                            <div className="flex items-center gap-2">
                                <span className="h-2 w-2 rounded-full bg-green-500" />
                                Authentication
                            </div>
                            <div className="flex items-center gap-2">
                                <span className="h-2 w-2 rounded-full bg-amber-500" />
                                Email Analysis
                            </div>
                            <div className="flex items-center gap-2">
                                <span className="h-2 w-2 rounded-full bg-muted-foreground" />
                                Conversation Loop
                            </div>
                        </div>
                    </div>
                </div>
            </main>
        </div>
    );
}
