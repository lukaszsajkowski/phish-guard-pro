"use client";

import { useState } from "react";
import { ChevronDown, ChevronUp, Info, Zap } from "lucide-react";
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
    /** US-040: When true, shows CTA to enrich IOCs for a more accurate score. */
    hasUnenrichedIOCs?: boolean;
}

export function RiskScoreBreakdown({
    breakdown,
    hasUnenrichedIOCs = false,
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
                "overflow-hidden transition-all duration-300 border-l-4 bg-card",
                getRiskLevelBorder(riskLevel),
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
                    <div className="flex items-center gap-4">
                        {/* Score display — no redundant "Risk Score" label (section header above provides it) */}
                        <div className="flex items-baseline gap-1.5">
                            <span
                                data-testid="total-score"
                                className={`text-2xl font-bold tracking-tight ${getRiskScoreColor(totalScore)}`}
                            >
                                {totalScore.toFixed(1)}
                            </span>
                            <span className="text-sm font-medium text-muted-foreground/50">/10</span>
                        </div>

                        <div className="h-8 w-px bg-border/40" />

                        {/* Risk level badge */}
                        <span
                            data-testid="risk-level-badge"
                            className={`inline-flex items-center rounded-md px-2.5 py-1 text-xs font-bold uppercase tracking-wide ${getRiskLevelColor(riskLevel)} ${getRiskLevelBg(riskLevel)}`}
                        >
                            {getRiskLevelLabel(riskLevel)}
                        </span>
                    </div>

                    {/* Expand/collapse indicator — styled as a subtle pill to look clickable */}
                    <div className="flex items-center gap-1.5 rounded-full bg-muted/40 px-2.5 py-1 text-xs font-medium text-muted-foreground hover:bg-muted/60 hover:text-foreground transition-colors">
                        <span>{isExpanded ? "Hide" : "Details"}</span>
                        {isExpanded ? (
                            <ChevronUp className="h-3.5 w-3.5" />
                        ) : (
                            <ChevronDown className="h-3.5 w-3.5" />
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
                            <div className="h-2.5 bg-secondary/50 rounded-full overflow-hidden">
                                <div
                                    data-testid="total-score-bar"
                                    className={`h-full transition-all duration-700 ease-out rounded-full ${getRiskScoreBarColor(totalScore)}`}
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

                        {/* US-040: CTA when unenriched IOCs could improve score accuracy */}
                        {hasUnenrichedIOCs && (
                            <div className="flex items-center gap-2 rounded-md bg-primary/5 border border-primary/20 p-3 text-xs text-primary/80">
                                <Zap className="h-4 w-4 shrink-0 text-primary/60" />
                                <p>
                                    Enrich IOCs to refine score accuracy — reputation data affects the IOC Quality component.
                                </p>
                            </div>
                        )}

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
