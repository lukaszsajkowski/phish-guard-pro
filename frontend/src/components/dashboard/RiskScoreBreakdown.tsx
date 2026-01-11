"use client";

import { useState } from "react";
import { ChevronDown, ChevronUp, Info } from "lucide-react";
import type { RiskScoreBreakdown as RiskScoreBreakdownType } from "@/types/schemas";
import {
    RISK_COMPONENT_LABELS,
    RISK_COMPONENT_ICONS,
    RISK_COMPONENT_DESCRIPTIONS,
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

interface RiskScoreBreakdownProps {
    breakdown: RiskScoreBreakdownType;
    isLoading?: boolean;
}

export function RiskScoreBreakdown({
    breakdown,
    isLoading = false,
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
        <div
            data-testid="risk-score-breakdown"
            className={`rounded-lg border ${getRiskLevelBorder(riskLevel)} ${getRiskLevelBg(riskLevel)} overflow-hidden transition-all duration-300`}
        >
            {/* Header - Always visible */}
            <button
                data-testid="breakdown-toggle"
                onClick={() => setIsExpanded(!isExpanded)}
                className="w-full flex items-center justify-between p-4 hover:bg-black/5 transition-colors"
                aria-expanded={isExpanded}
                aria-controls="breakdown-content"
            >
                <div className="flex items-center gap-4">
                    {/* Score display */}
                    <div className="flex items-baseline gap-1">
                        <span
                            data-testid="total-score"
                            className={`text-4xl font-bold ${getRiskScoreColor(totalScore)}`}
                        >
                            {totalScore.toFixed(1)}
                        </span>
                        <span className="text-sm text-muted-foreground">/10</span>
                    </div>

                    {/* Risk level badge */}
                    <span
                        data-testid="risk-level-badge"
                        className={`inline-flex items-center rounded-full px-3 py-1 text-sm font-medium ${getRiskLevelColor(riskLevel)} ${getRiskLevelBg(riskLevel)}`}
                    >
                        {getRiskLevelLabel(riskLevel)}
                    </span>
                </div>

                {/* Expand/collapse indicator */}
                <div className="flex items-center gap-2 text-sm text-muted-foreground">
                    <span>{isExpanded ? "Hide" : "Show"} breakdown</span>
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
                className={`overflow-hidden transition-all duration-300 ease-in-out ${isExpanded ? "max-h-[800px] opacity-100" : "max-h-0 opacity-0"
                    }`}
            >
                <div className="px-4 pb-4 space-y-3 border-t border-border/30">
                    {/* Progress bar */}
                    <div className="pt-3">
                        <div className="h-2 bg-muted/30 rounded-full overflow-hidden">
                            <div
                                data-testid="total-score-bar"
                                className={`h-full transition-all duration-500 ${getRiskScoreBarColor(totalScore)}`}
                                style={{ width: `${(totalScore / 10) * 100}%` }}
                            />
                        </div>
                    </div>

                    {/* Component breakdown */}
                    <div className="space-y-2">
                        {sortedComponents.map((component) => {
                            const componentType = component.component as RiskComponentType;
                            const Icon = RISK_COMPONENT_ICONS[componentType];
                            const label = RISK_COMPONENT_LABELS[componentType];
                            const description = RISK_COMPONENT_DESCRIPTIONS[componentType];
                            const weightPercent = RISK_COMPONENT_WEIGHTS[componentType];

                            // Calculate percentage of max (10) for progress bar
                            const progressPercent = (component.raw_score / 10) * 100;

                            return (
                                <div
                                    key={component.component}
                                    data-testid={`component-${component.component}`}
                                    className="bg-background/50 rounded-md p-3"
                                >
                                    {/* Component header */}
                                    <div className="flex items-center justify-between mb-2">
                                        <div className="flex items-center gap-2">
                                            <Icon className="h-4 w-4 text-muted-foreground" />
                                            <span className="text-sm font-medium">
                                                {label}
                                            </span>
                                            <span className="text-xs text-muted-foreground">
                                                ({weightPercent}%)
                                            </span>
                                        </div>
                                        <div className="flex items-center gap-2">
                                            <span className="text-sm font-semibold">
                                                {component.raw_score.toFixed(1)}
                                            </span>
                                            <span className="text-xs text-muted-foreground">
                                                / 10
                                            </span>
                                        </div>
                                    </div>

                                    {/* Progress bar */}
                                    <div className="h-1.5 bg-muted/30 rounded-full overflow-hidden mb-2">
                                        <div
                                            className={`h-full transition-all duration-300 ${getComponentScoreBg(component.raw_score)}`}
                                            style={{ width: `${progressPercent}%` }}
                                        />
                                    </div>

                                    {/* Explanation */}
                                    <p className="text-xs text-muted-foreground">
                                        {component.explanation}
                                    </p>
                                </div>
                            );
                        })}
                    </div>

                    {/* Info footer */}
                    <div className="flex items-start gap-2 pt-2 text-xs text-muted-foreground">
                        <Info className="h-3 w-3 mt-0.5 flex-shrink-0" />
                        <p>
                            Risk score is calculated from 6 weighted components.
                            Higher scores indicate more sophisticated or dangerous phishing attempts.
                        </p>
                    </div>
                </div>
            </div>
        </div>
    );
}
