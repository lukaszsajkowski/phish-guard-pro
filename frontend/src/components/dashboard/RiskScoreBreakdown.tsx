"use client";

import { useState } from "react";
import { ChevronDown, ChevronUp, Info } from "lucide-react";
import type { RiskScoreBreakdown as RiskScoreBreakdownType } from "@/types/schemas";
import {
    RISK_COMPONENT_LABELS,
    RISK_COMPONENT_ICONS,
    RISK_COMPONENT_WEIGHTS,
    RISK_COMPONENT_ORDER,
    getComponentScoreBg,
    getRiskLevelColor,
    getRiskLevelBg,
    getRiskLevelBorder,
    getRiskLevelLabel,
    type RiskComponentType,
} from "@/lib/constants/risk";
import {
    getRiskScoreColor,
    getRiskScoreBarColor,
} from "@/lib/constants/ioc";
import { Card, CardContent } from "@/components/ui/card";
import { cn } from "@/lib/utils";

interface RiskScoreBreakdownProps {
    breakdown: RiskScoreBreakdownType;
    isLoading?: boolean;
}

export function RiskScoreBreakdown({
    breakdown,
}: RiskScoreBreakdownProps) {
    const [isExpanded, setIsExpanded] = useState(false);

    const riskLevel = breakdown.risk_level;
    const totalScore = breakdown.total_score;

    // Sort components by the defined order
    const sortedComponents = [...breakdown.components].sort((a, b) => {
        const orderA = RISK_COMPONENT_ORDER.indexOf(a.component as RiskComponentType);
        const orderB = RISK_COMPONENT_ORDER.indexOf(b.component as RiskComponentType);
        return orderA - orderB;
    });

    return (
        <Card
            className={cn(
                "overflow-hidden transition-all duration-300 border-l-4",
                getRiskLevelBorder(riskLevel),
                riskLevel === "high"
                    ? "bg-red-50/10 dark:bg-red-950/10"
                    : riskLevel === "medium"
                        ? "bg-yellow-50/10 dark:bg-yellow-950/10"
                        : "bg-card"
            )}
        >
            <div className="w-full flex flex-col">
                {/* Header - Always visible */}
                <button
                    data-testid="breakdown-toggle"
                    aria-expanded={isExpanded}
                    aria-controls="breakdown-content"
                    onClick={() => setIsExpanded(!isExpanded)}
                    className="w-full flex items-center justify-between p-3 hover:bg-muted/30 transition-colors"
                >
                    <div className="flex items-center gap-6">
                        {/* Score display */}
                        <div className="flex flex-col items-start gap-0.5">
                            <span className="text-xs uppercase tracking-wider text-muted-foreground font-semibold">Risk Score</span>
                            <div className="flex items-baseline gap-1.5">
                                <span
                                    data-testid="total-score"
                                    className={`text-3xl font-bold tracking-tight ${getRiskScoreColor(totalScore)}`}
                                >
                                    {totalScore.toFixed(1)}
                                </span>
                                <span className="text-sm font-medium text-muted-foreground/60">/ 10</span>
                            </div>
                        </div>

                        <div className="h-10 w-px bg-border/50 mx-2" />

                        {/* Risk level badge */}
                        <div className="flex flex-col items-start gap-1">
                            <span className="text-xs uppercase tracking-wider text-muted-foreground font-semibold">Level</span>
                            <span
                                data-testid="risk-level-badge"
                                className={`inline-flex items-center rounded-md px-2.5 py-0.5 text-sm font-semibold ring-1 ring-inset ${getRiskLevelColor(riskLevel)} ${getRiskLevelBg(riskLevel)} ring-opacity-20`}
                            >
                                {getRiskLevelLabel(riskLevel)}
                            </span>
                        </div>
                    </div>

                    {/* Expand/collapse indicator */}
                    <div className="flex items-center gap-2 text-sm font-medium text-muted-foreground hover:text-foreground transition-colors">
                        <span>{isExpanded ? "Hide breakdown" : "Show breakdown"}</span>
                        {isExpanded ? (
                            <ChevronUp className="h-4 w-4" />
                        ) : (
                            <ChevronDown className="h-4 w-4" />
                        )}
                    </div>
                </button>

                {/* Expandable content */}
                <div
                    id="breakdown-content"
                    data-testid="breakdown-content"
                    className={cn(
                        "overflow-hidden transition-all duration-300 ease-in-out",
                        isExpanded ? "max-h-[800px] opacity-100" : "max-h-0 opacity-0"
                    )}
                >
                    <CardContent className="px-3 pb-3 pt-0 space-y-4">

                        {/* Total score progress bar */}
                        <div className="space-y-1.5 mt-2">
                            <div className="h-2.5 bg-secondary/50 rounded-full overflow-hidden shadow-inner">
                                <div
                                    data-testid="total-score-bar"
                                    className={`h-full transition-all duration-700 ease-out rounded-full shadow-sm ${getRiskScoreBarColor(totalScore)}`}
                                    style={{ width: `${(totalScore / 10) * 100}%` }}
                                />
                            </div>
                        </div>

                        {/* Component breakdown */}
                        <div className="grid gap-3">
                            {sortedComponents.map((component) => {
                                const componentType = component.component as RiskComponentType;
                                const Icon = RISK_COMPONENT_ICONS[componentType] || Info;
                                const label = RISK_COMPONENT_LABELS[componentType];
                                const weightPercent = RISK_COMPONENT_WEIGHTS[componentType];
                                const progressPercent = (component.raw_score / 10) * 100;

                                return (
                                    <div
                                        key={component.component}
                                        data-testid={`component-${component.component}`}
                                        className="relative group rounded-lg border bg-card hover:bg-muted/20 transition-colors p-3"
                                    >
                                        <div className="flex items-start gap-3">
                                            <div className="mt-1 p-2 rounded-md bg-muted/40 text-foreground/70">
                                                <Icon className="h-4 w-4" />
                                            </div>
                                            <div className="flex-1 space-y-2">
                                                <div className="flex items-start justify-between">
                                                    <div>
                                                        <div className="flex items-center gap-2">
                                                            <h4 className="text-sm font-semibold leading-none">{label}</h4>
                                                            <span className="text-xs px-1.5 py-0.5 rounded-full bg-muted text-muted-foreground font-medium">
                                                                ({weightPercent}%)
                                                            </span>
                                                        </div>
                                                        <p className="text-xs text-muted-foreground mt-1 line-clamp-2 leading-relaxed">
                                                            {component.explanation}
                                                        </p>
                                                    </div>
                                                    <div className="text-right">
                                                        <div className="text-sm font-bold font-mono">
                                                            {component.raw_score.toFixed(1)}<span className="text-muted-foreground text-xs font-normal">/10</span>
                                                        </div>
                                                    </div>
                                                </div>

                                                {/* Mini Progress Bar */}
                                                <div className="h-1.5 w-full bg-secondary/50 rounded-full overflow-hidden">
                                                    <div
                                                        className={cn("h-full rounded-full transition-all duration-500", getComponentScoreBg(component.raw_score))}
                                                        style={{ width: `${progressPercent}%` }}
                                                    />
                                                </div>
                                            </div>
                                        </div>
                                    </div>
                                );
                            })}
                        </div>

                        {/* Info footer */}
                        <div className="flex items-center gap-2 rounded-md bg-muted/30 p-3 text-xs text-muted-foreground">
                            <Info className="h-4 w-4 shrink-0 text-primary/60" />
                            <p>
                                Risk score is calculated from weighted components. Higher scores indicate more sophisticated attacks.
                            </p>
                        </div>
                    </CardContent>
                </div>
            </div>
        </Card>
    );
}
