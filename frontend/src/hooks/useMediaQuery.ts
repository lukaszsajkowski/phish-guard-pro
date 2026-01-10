"use client";

import { useSyncExternalStore } from "react";

/**
 * Custom hook to track media query matches
 * @param query - CSS media query string (e.g., "(min-width: 1280px)")
 * @returns boolean indicating if the media query matches
 */
export function useMediaQuery(query: string): boolean {
    const subscribe = (callback: () => void) => {
        if (typeof window === "undefined") {
            return () => {};
        }
        const mediaQuery = window.matchMedia(query);
        mediaQuery.addEventListener("change", callback);
        return () => mediaQuery.removeEventListener("change", callback);
    };

    const getSnapshot = () => {
        if (typeof window === "undefined") {
            return false;
        }
        return window.matchMedia(query).matches;
    };

    const getServerSnapshot = () => false;

    return useSyncExternalStore(subscribe, getSnapshot, getServerSnapshot);
}
