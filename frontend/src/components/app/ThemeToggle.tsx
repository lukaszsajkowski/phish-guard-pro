"use client";

import { Sun, Moon } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useTheme } from "@/components/theme-provider";
import {
    Tooltip,
    TooltipContent,
    TooltipProvider,
    TooltipTrigger,
} from "@/components/ui/tooltip";

export function ThemeToggle() {
  const { theme, toggleTheme } = useTheme();

  const label = theme === "dark" ? "Switch to light mode" : "Switch to dark mode";

  return (
    <TooltipProvider>
      <Tooltip>
        <TooltipTrigger asChild>
          <Button
            variant="ghost"
            size="icon"
            onClick={toggleTheme}
            aria-label={label}
            data-testid="theme-toggle"
            className="relative h-9 w-9"
          >
      {/* Sun icon — visible in dark mode (click to switch to light) */}
      <Sun
        className={`h-4 w-4 transition-all duration-200 ${
          theme === "dark"
            ? "scale-100 opacity-100 rotate-0"
            : "scale-0 opacity-0 rotate-90"
        } absolute`}
      />
      {/* Moon icon — visible in light mode (click to switch to dark) */}
      <Moon
        className={`h-4 w-4 transition-all duration-200 ${
          theme === "light"
            ? "scale-100 opacity-100 rotate-0"
            : "scale-0 opacity-0 -rotate-90"
        } absolute`}
      />
            <span className="sr-only">Toggle theme</span>
          </Button>
        </TooltipTrigger>
        <TooltipContent>
          <p>{label}</p>
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
}
