"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
    LayoutDashboard,
    History,
    PlusCircle,
    LogOut,
    Loader2,
    Shield,
    User as UserIcon,
} from "lucide-react";
import { User } from "@supabase/supabase-js";
import { Button } from "@/components/ui/button";

interface AppSidebarProps {
    user: User;
    onLogout: () => void;
    isLoggingOut?: boolean;
    onNewSession?: () => void;
}

interface NavItem {
    href: string;
    label: string;
    icon: React.ReactNode;
}

export function AppSidebar({
    user,
    onLogout,
    isLoggingOut = false,
    onNewSession,
}: AppSidebarProps) {
    const pathname = usePathname();

    const navItems: NavItem[] = [
        {
            href: "/dashboard",
            label: "Dashboard",
            icon: <LayoutDashboard className="h-5 w-5" />,
        },
        {
            href: "/history",
            label: "History",
            icon: <History className="h-5 w-5" />,
        },
    ];

    const isActive = (href: string) => {
        if (href === "/dashboard") {
            return pathname === "/dashboard" || pathname.startsWith("/dashboard?");
        }
        if (href === "/history") {
            return pathname === "/history" || pathname.startsWith("/history/");
        }
        return pathname === href;
    };

    return (
        <aside
            className="flex flex-col h-full w-64 bg-card border-r border-border"
            data-testid="app-sidebar"
        >
            {/* Header with logo */}
            <div className="flex items-center h-16 px-4 border-b border-border">
                <Link
                    href="/dashboard"
                    className="flex items-center gap-2"
                >
                    <Shield className="h-7 w-7 text-primary flex-shrink-0" />
                    <span className="font-bold text-lg tracking-tight">
                        PhishGuard
                    </span>
                </Link>
            </div>

            {/* Navigation */}
            <nav className="flex-1 py-4 px-2 space-y-1">
                {navItems.map((item) => (
                    <Link
                        key={item.href}
                        href={item.href}
                        className={`flex items-center gap-3 px-3 py-2.5 rounded-lg transition-colors hover:bg-accent hover:text-accent-foreground ${
                            isActive(item.href)
                                ? "bg-primary/10 text-primary font-medium"
                                : "text-muted-foreground"
                        }`}
                        data-testid={`sidebar-nav-${item.href.replace("/", "")}`}
                    >
                        {item.icon}
                        <span>{item.label}</span>
                    </Link>
                ))}

                {/* New Session - Quick Action */}
                <button
                    onClick={onNewSession}
                    className="flex items-center gap-3 px-3 py-2.5 rounded-lg transition-colors w-full hover:bg-accent hover:text-accent-foreground text-muted-foreground"
                    data-testid="sidebar-new-session"
                >
                    <PlusCircle className="h-5 w-5" />
                    <span>New Session</span>
                </button>
            </nav>

            {/* User info and logout */}
            <div className="border-t border-border p-3">
                <div className="flex items-center gap-3 mb-3">
                    <div className="flex-shrink-0 w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center">
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
                    className="w-full justify-start text-muted-foreground hover:text-destructive hover:bg-destructive/10"
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
