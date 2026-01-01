"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Shield, LogOut, Loader2 } from "lucide-react";
import Link from "next/link";
import { createClient, User } from "@supabase/supabase-js";
import { EmailInput } from "@/components/app/email-input";

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

    const handleAnalyze = async (emailContent: string) => {
        try {
            const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/v1/analysis`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ content: emailContent }),
            });

            if (!response.ok) {
                throw new Error('Analysis failed');
            }

            const data = await response.json();
            console.log("Analysis started:", data);
            // In US-004 we will handle the response/navigation

        } catch (error) {
            console.error("Error analyzing email:", error);
            // TODO: generic error handling UI
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
                    <div className="flex items-center gap-4">
                        <span className="text-sm text-muted-foreground">
                            {user?.email}
                        </span>
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
                </div>
            </header>

            {/* Main content */}
            <main className="flex flex-1 flex-col items-center justify-center px-4 py-12">
                <EmailInput onAnalyze={handleAnalyze} />
            </main>
        </div>
    );
}
