"use client";

import { useEffect, useState, useCallback, ReactNode } from "react";
import { useRouter } from "next/navigation";
import { createClient, User } from "@supabase/supabase-js";
import { Loader2 } from "lucide-react";
import { AppSidebar } from "./AppSidebar";
import { useSidebarState } from "@/hooks/useSidebarState";
import { cn } from "@/lib/utils";

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

    const {
        isCollapsed,
        isEffectivelyCollapsed,
        toggleCollapsed,
        setIsHovered,
    } = useSidebarState();

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

    const handleMouseEnter = useCallback(() => {
        if (isCollapsed) {
            setIsHovered(true);
        }
    }, [isCollapsed, setIsHovered]);

    const handleMouseLeave = useCallback(() => {
        setIsHovered(false);
    }, [setIsHovered]);

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
            {/* Fixed sidebar */}
            <div
                className={cn(
                    "fixed left-0 top-0 h-full z-40 transition-all duration-300 ease-in-out",
                    isEffectivelyCollapsed ? "w-16" : "w-64"
                )}
                data-testid="sidebar-container"
            >
                <AppSidebar
                    user={user}
                    onLogout={handleLogout}
                    isLoggingOut={isLoggingOut}
                    onNewSession={onNewSession}
                    isCollapsed={isCollapsed}
                    isEffectivelyCollapsed={isEffectivelyCollapsed}
                    onToggleCollapse={toggleCollapsed}
                    onMouseEnter={handleMouseEnter}
                    onMouseLeave={handleMouseLeave}
                />
            </div>

            {/* Main content area */}
            <main
                className={cn(
                    "flex-1 transition-all duration-300 ease-in-out",
                    isEffectivelyCollapsed ? "ml-16" : "ml-64"
                )}
                data-testid="main-content"
            >
                {children}
            </main>
        </div>
    );
}
