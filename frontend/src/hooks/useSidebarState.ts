"use client";

import { useState, useCallback, useSyncExternalStore } from "react";
import { useMediaQuery } from "./useMediaQuery";

const SIDEBAR_STATE_KEY = "phishguard-sidebar-collapsed";
const BREAKPOINT = 1280; // xl breakpoint

interface SidebarState {
    /** Whether the sidebar is collapsed */
    isCollapsed: boolean;
    /** Whether the sidebar is temporarily expanded (on hover) */
    isHovered: boolean;
    /** Toggle the collapsed state */
    toggleCollapsed: () => void;
    /** Set hover state */
    setIsHovered: (hovered: boolean) => void;
    /** Effective collapsed state (collapsed AND not hovered) */
    isEffectivelyCollapsed: boolean;
}

// External store for localStorage
function subscribeToLocalStorage(callback: () => void) {
    window.addEventListener("storage", callback);
    return () => window.removeEventListener("storage", callback);
}

function getLocalStorageSnapshot(): string | null {
    if (typeof window === "undefined") {
        return null;
    }
    return localStorage.getItem(SIDEBAR_STATE_KEY);
}

function getLocalStorageServerSnapshot(): string | null {
    return null;
}

/**
 * Hook to manage sidebar collapsed state with:
 * - localStorage persistence
 * - Responsive default (collapsed on screens < 1280px)
 * - Hover expansion support
 */
export function useSidebarState(): SidebarState {
    const isLargeScreen = useMediaQuery(`(min-width: ${BREAKPOINT}px)`);
    const [isHovered, setIsHovered] = useState(false);

    // Read from localStorage using useSyncExternalStore
    const storedValue = useSyncExternalStore(
        subscribeToLocalStorage,
        getLocalStorageSnapshot,
        getLocalStorageServerSnapshot
    );

    // Derive collapsed state from stored value or screen size default
    const isCollapsed =
        storedValue !== null ? storedValue === "true" : !isLargeScreen;

    const toggleCollapsed = useCallback(() => {
        const newValue = !isCollapsed;
        localStorage.setItem(SIDEBAR_STATE_KEY, String(newValue));
        // Manually dispatch storage event to trigger re-render
        window.dispatchEvent(new StorageEvent("storage", { key: SIDEBAR_STATE_KEY }));
    }, [isCollapsed]);

    const handleSetIsHovered = useCallback((hovered: boolean) => {
        setIsHovered(hovered);
    }, []);

    // Sidebar is effectively collapsed when collapsed AND not being hovered
    const isEffectivelyCollapsed = isCollapsed && !isHovered;

    return {
        isCollapsed,
        isHovered,
        toggleCollapsed,
        setIsHovered: handleSetIsHovered,
        isEffectivelyCollapsed,
    };
}
