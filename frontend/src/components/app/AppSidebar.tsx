"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
    History,
    PlusCircle,
    LogOut,
    Loader2,
    Shield,
    User as UserIcon,
} from "lucide-react";
import { User } from "@supabase/supabase-js";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

interface AppSidebarProps {
    user: User;
    onLogout: () => void;
    isLoggingOut?: boolean;
    onNewSession?: () => void;
}

export function AppSidebar({
    user,
    onLogout,
    isLoggingOut = false,
    onNewSession,
}: AppSidebarProps) {
    const pathname = usePathname();

    const isHistoryActive =
        pathname === "/history" || pathname.startsWith("/history/");

    return (
        <aside
            className="flex flex-col h-full w-64 bg-card border-r border-border"
            data-testid="app-sidebar"
        >
            {/* Header with logo */}
            <div className="flex items-center h-16 px-4 border-b border-border">
                <Link
                    href="/dashboard"
                    className="flex items-center gap-2 cursor-pointer"
                >
                    <Shield className="h-7 w-7 text-primary" />
                    <span className="font-bold text-lg tracking-tight">
                        PhishGuard
                    </span>
                </Link>
            </div>

            {/* Navigation */}
            <nav className="flex-1 py-4 px-2 space-y-1">
                {/* New Session */}
                <NavItem
                    icon={<PlusCircle className="h-5 w-5" />}
                    label="New Session"
                    onClick={onNewSession}
                    testId="sidebar-new-session"
                />

                {/* History */}
                <NavItem
                    icon={<History className="h-5 w-5" />}
                    label="History"
                    href="/history"
                    isActive={isHistoryActive}
                    testId="sidebar-nav-history"
                />
            </nav>

            {/* User info and logout */}
            <div className="border-t border-border p-3">
                <div className="flex items-center gap-3 mb-3">
                    <div className="w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center">
                        <UserIcon className="h-4 w-4 text-primary" />
                    </div>
                    <p
                        className="text-sm font-medium truncate max-w-[180px]"
                        title={user.email || ""}
                        data-testid="sidebar-user-email"
                    >
                        {user.email}
                    </p>
                </div>

                <Button
                    variant="ghost"
                    size="sm"
                    onClick={onLogout}
                    disabled={isLoggingOut}
                    className="w-full justify-start cursor-pointer text-muted-foreground hover:text-destructive hover:bg-destructive/10"
                    data-testid="sidebar-logout-button"
                >
                    {isLoggingOut ? (
                        <Loader2 className="h-4 w-4 animate-spin" />
                    ) : (
                        <LogOut className="h-4 w-4" />
                    )}
                    <span className="ml-2">
                        {isLoggingOut ? "Signing out..." : "Sign out"}
                    </span>
                </Button>
            </div>
        </aside>
    );
}

interface NavItemProps {
    icon: React.ReactNode;
    label: string;
    href?: string;
    onClick?: () => void;
    isActive?: boolean;
    testId?: string;
}

function NavItem({
    icon,
    label,
    href,
    onClick,
    isActive = false,
    testId,
}: NavItemProps) {
    const baseClasses = cn(
        "flex items-center gap-3 px-3 py-2.5 rounded-lg transition-colors w-full cursor-pointer",
        "hover:bg-accent hover:text-accent-foreground",
        isActive
            ? "bg-primary/10 text-primary font-medium"
            : "text-muted-foreground"
    );

    const content = (
        <>
            {icon}
            <span>{label}</span>
        </>
    );

    if (href) {
        return (
            <Link href={href} className={baseClasses} data-testid={testId}>
                {content}
            </Link>
        );
    }

    return (
        <button onClick={onClick} className={baseClasses} data-testid={testId}>
            {content}
        </button>
    );
}
