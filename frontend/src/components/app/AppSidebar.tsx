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
    PanelLeftClose,
    PanelLeft,
} from "lucide-react";
import { User } from "@supabase/supabase-js";
import { Button } from "@/components/ui/button";
import {
    Tooltip,
    TooltipContent,
    TooltipProvider,
    TooltipTrigger,
} from "@/components/ui/tooltip";
import { cn } from "@/lib/utils";

interface AppSidebarProps {
    user: User;
    onLogout: () => void;
    isLoggingOut?: boolean;
    onNewSession?: () => void;
    isCollapsed?: boolean;
    isEffectivelyCollapsed?: boolean;
    onToggleCollapse?: () => void;
    onMouseEnter?: () => void;
    onMouseLeave?: () => void;
}

export function AppSidebar({
    user,
    onLogout,
    isLoggingOut = false,
    onNewSession,
    isCollapsed = false,
    isEffectivelyCollapsed = false,
    onToggleCollapse,
    onMouseEnter,
    onMouseLeave,
}: AppSidebarProps) {
    const pathname = usePathname();

    const isHistoryActive =
        pathname === "/history" || pathname.startsWith("/history/");

    return (
        <TooltipProvider delayDuration={0}>
            <aside
                className={cn(
                    "flex flex-col h-full bg-card border-r border-border transition-all duration-300 ease-in-out",
                    isEffectivelyCollapsed ? "w-16" : "w-64"
                )}
                data-testid="app-sidebar"
                onMouseEnter={onMouseEnter}
                onMouseLeave={onMouseLeave}
            >
                {/* Header with logo */}
                <div className="flex items-center h-16 px-4 border-b border-border">
                    <Link
                        href="/dashboard"
                        className="flex items-center gap-2 cursor-pointer overflow-hidden"
                    >
                        <Shield className="h-7 w-7 text-primary flex-shrink-0" />
                        <span
                            className={cn(
                                "font-bold text-lg tracking-tight whitespace-nowrap transition-all duration-300",
                                isEffectivelyCollapsed
                                    ? "opacity-0 w-0"
                                    : "opacity-100 w-auto"
                            )}
                        >
                            PhishGuard
                        </span>
                    </Link>
                </div>

                {/* Navigation */}
                <nav className="flex-1 py-4 px-2 space-y-1">
                    {/* New Session */}
                    <NavItem
                        icon={<PlusCircle className="h-5 w-5 flex-shrink-0" />}
                        label="New Session"
                        onClick={onNewSession}
                        isCollapsed={isEffectivelyCollapsed}
                        testId="sidebar-new-session"
                    />

                    {/* History */}
                    <NavItem
                        icon={<History className="h-5 w-5 flex-shrink-0" />}
                        label="History"
                        href="/history"
                        isActive={isHistoryActive}
                        isCollapsed={isEffectivelyCollapsed}
                        testId="sidebar-nav-history"
                    />
                </nav>

                {/* Collapse toggle button */}
                <div className="px-2 py-2 border-t border-border">
                    <Tooltip>
                        <TooltipTrigger asChild>
                            <button
                                onClick={onToggleCollapse}
                                className={cn(
                                    "flex items-center gap-3 px-3 py-2.5 rounded-lg transition-colors w-full cursor-pointer",
                                    "hover:bg-accent hover:text-accent-foreground text-muted-foreground"
                                )}
                                data-testid="sidebar-collapse-toggle"
                                aria-label={
                                    isCollapsed
                                        ? "Expand sidebar"
                                        : "Collapse sidebar"
                                }
                            >
                                {isCollapsed ? (
                                    <PanelLeft className="h-5 w-5 flex-shrink-0" />
                                ) : (
                                    <PanelLeftClose className="h-5 w-5 flex-shrink-0" />
                                )}
                                <span
                                    className={cn(
                                        "whitespace-nowrap transition-all duration-300",
                                        isEffectivelyCollapsed
                                            ? "opacity-0 w-0 overflow-hidden"
                                            : "opacity-100 w-auto"
                                    )}
                                >
                                    {isCollapsed ? "Expand" : "Collapse"}
                                </span>
                            </button>
                        </TooltipTrigger>
                        {isEffectivelyCollapsed && (
                            <TooltipContent side="right">
                                {isCollapsed ? "Expand sidebar" : "Collapse sidebar"}
                            </TooltipContent>
                        )}
                    </Tooltip>
                </div>

                {/* User info and logout */}
                <div className="border-t border-border p-3">
                    <div
                        className={cn(
                            "flex items-center gap-3 mb-3",
                            isEffectivelyCollapsed && "justify-center"
                        )}
                    >
                        <Tooltip>
                            <TooltipTrigger asChild>
                                <div className="flex-shrink-0 w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center cursor-default">
                                    <UserIcon className="h-4 w-4 text-primary" />
                                </div>
                            </TooltipTrigger>
                            {isEffectivelyCollapsed && (
                                <TooltipContent side="right">
                                    {user.email}
                                </TooltipContent>
                            )}
                        </Tooltip>
                        <p
                            className={cn(
                                "text-sm font-medium truncate transition-all duration-300",
                                isEffectivelyCollapsed
                                    ? "opacity-0 w-0 overflow-hidden"
                                    : "opacity-100 max-w-[180px]"
                            )}
                            title={user.email || ""}
                            data-testid="sidebar-user-email"
                        >
                            {user.email}
                        </p>
                    </div>

                    <Tooltip>
                        <TooltipTrigger asChild>
                            <Button
                                variant="ghost"
                                size="sm"
                                onClick={onLogout}
                                disabled={isLoggingOut}
                                className={cn(
                                    "w-full cursor-pointer text-muted-foreground hover:text-destructive hover:bg-destructive/10",
                                    isEffectivelyCollapsed
                                        ? "justify-center px-0"
                                        : "justify-start"
                                )}
                                data-testid="sidebar-logout-button"
                            >
                                {isLoggingOut ? (
                                    <Loader2 className="h-4 w-4 animate-spin flex-shrink-0" />
                                ) : (
                                    <LogOut className="h-4 w-4 flex-shrink-0" />
                                )}
                                <span
                                    className={cn(
                                        "ml-2 whitespace-nowrap transition-all duration-300",
                                        isEffectivelyCollapsed
                                            ? "opacity-0 w-0 overflow-hidden sr-only"
                                            : "opacity-100 w-auto"
                                    )}
                                >
                                    {isLoggingOut ? "Signing out..." : "Sign out"}
                                </span>
                            </Button>
                        </TooltipTrigger>
                        {isEffectivelyCollapsed && (
                            <TooltipContent side="right">
                                {isLoggingOut ? "Signing out..." : "Sign out"}
                            </TooltipContent>
                        )}
                    </Tooltip>
                </div>
            </aside>
        </TooltipProvider>
    );
}

interface NavItemProps {
    icon: React.ReactNode;
    label: string;
    href?: string;
    onClick?: () => void;
    isActive?: boolean;
    isCollapsed: boolean;
    testId?: string;
}

function NavItem({
    icon,
    label,
    href,
    onClick,
    isActive = false,
    isCollapsed,
    testId,
}: NavItemProps) {
    const baseClasses = cn(
        "flex items-center gap-3 px-3 py-2.5 rounded-lg transition-colors w-full cursor-pointer",
        "hover:bg-accent hover:text-accent-foreground",
        isActive
            ? "bg-primary/10 text-primary font-medium"
            : "text-muted-foreground",
        isCollapsed && "justify-center px-0"
    );

    const content = (
        <>
            {icon}
            <span
                className={cn(
                    "whitespace-nowrap transition-all duration-300",
                    isCollapsed
                        ? "opacity-0 w-0 overflow-hidden"
                        : "opacity-100 w-auto"
                )}
            >
                {label}
            </span>
        </>
    );

    const item = href ? (
        <Link href={href} className={baseClasses} data-testid={testId}>
            {content}
        </Link>
    ) : (
        <button onClick={onClick} className={baseClasses} data-testid={testId}>
            {content}
        </button>
    );

    return (
        <Tooltip>
            <TooltipTrigger asChild>{item}</TooltipTrigger>
            {isCollapsed && (
                <TooltipContent side="right">{label}</TooltipContent>
            )}
        </Tooltip>
    );
}
