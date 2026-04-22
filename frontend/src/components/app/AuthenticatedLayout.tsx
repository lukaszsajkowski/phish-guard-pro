"use client";

import { useEffect, useState, useCallback, ReactNode } from "react";
import { useRouter } from "next/navigation";
import { createClient, User } from "@supabase/supabase-js";
import { Loader2, Menu, Shield } from "lucide-react";
import { AppSidebar } from "./AppSidebar";
import {
    Sheet,
    SheetContent,
    SheetHeader,
    SheetTitle,
    SheetTrigger,
} from "@/components/ui/sheet";

interface AuthenticatedLayoutProps {
    children: ReactNode;
    onNewSession?: () => void;
}

export function AuthenticatedLayout({
    children,
    onNewSession,
}: AuthenticatedLayoutProps) {
    const router = useRouter();
    const [user, setUser] = useState<User | null>(null);
    const [isLoading, setIsLoading] = useState(true);
    const [isLoggingOut, setIsLoggingOut] = useState(false);

    // Auth check
    useEffect(() => {
        const checkAuth = async () => {
            const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL;
            const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;

            if (!supabaseUrl || !supabaseAnonKey) {
                router.push("/login");
                return;
            }

            const supabase = createClient(supabaseUrl, supabaseAnonKey);
            const {
                data: { user },
            } = await supabase.auth.getUser();

            if (!user) {
                router.push("/login");
                return;
            }

            setUser(user);
            setIsLoading(false);
        };

        checkAuth();
    }, [router]);

    const handleLogout = useCallback(async () => {
        setIsLoggingOut(true);

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
            setIsLoggingOut(false);
        }
    }, [router]);

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

    if (!user) {
        return null;
    }

    return (
        <div className="flex min-h-screen bg-background">
            {/* Mobile header with hamburger menu — visible below lg */}
            <div className="fixed top-0 left-0 right-0 z-50 flex items-center gap-3 border-b border-border bg-background px-4 h-14 lg:hidden">
                <Sheet>
                    <SheetTrigger asChild>
                        <button
                            className="inline-flex items-center justify-center rounded-md p-2 hover:bg-muted"
                            aria-label="Open navigation menu"
                        >
                            <Menu className="h-5 w-5" />
                        </button>
                    </SheetTrigger>
                    <SheetContent side="left" className="w-64 p-0">
                        <SheetHeader className="sr-only">
                            <SheetTitle>Navigation</SheetTitle>
                        </SheetHeader>
                        <AppSidebar
                            user={user}
                            onLogout={handleLogout}
                            isLoggingOut={isLoggingOut}
                            onNewSession={onNewSession}
                        />
                    </SheetContent>
                </Sheet>
                <div className="flex items-center gap-2">
                    <Shield className="h-5 w-5 text-primary" />
                    <span className="font-semibold">PhishGuard Pro</span>
                </div>
            </div>

            {/* Fixed sidebar — hidden on mobile, visible on lg+ */}
            <div
                className="fixed left-0 top-0 h-full w-64 z-40 hidden lg:block"
                data-testid="sidebar-container"
            >
                <AppSidebar
                    user={user}
                    onLogout={handleLogout}
                    isLoggingOut={isLoggingOut}
                    onNewSession={onNewSession}
                />
            </div>

            {/* Main content area — top padding for mobile header, left margin for desktop sidebar */}
            <main className="flex-1 pt-14 lg:pt-0 lg:ml-64" data-testid="main-content">
                {children}
            </main>
        </div>
    );
}
