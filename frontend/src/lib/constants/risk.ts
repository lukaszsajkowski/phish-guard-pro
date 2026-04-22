import {
    Target,
    Gem,
    Hash,
    MessageCircle,
    AlertTriangle,
    Search,
    type LucideIcon,
} from "lucide-react";
import type { RiskLevel } from "@/types/schemas";

/**
 * All possible risk component types
 */
export type RiskComponentType =
    | "attack_severity"
    | "ioc_quality"
    | "ioc_quantity"
    | "scammer_engagement"
    | "urgency_tactics"
    | "personalization";

/**
 * Display labels for risk components
 */
export const RISK_COMPONENT_LABELS: Record<RiskComponentType, string> = {
    attack_severity: "Attack Severity",
    ioc_quality: "IOC Quality",
    ioc_quantity: "IOC Quantity",
    scammer_engagement: "Scammer Engagement",
    urgency_tactics: "Urgency Tactics",
    personalization: "Personalization",
};

/**
 * Icons for risk components
 */
export const RISK_COMPONENT_ICONS: Record<RiskComponentType, LucideIcon> = {
    attack_severity: Target,
    ioc_quality: Gem,
    ioc_quantity: Hash,
    scammer_engagement: MessageCircle,
    urgency_tactics: AlertTriangle,
    personalization: Search,
};

/**
 * Descriptions for risk components
 */
export const RISK_COMPONENT_DESCRIPTIONS: Record<RiskComponentType, string> = {
    attack_severity:
        "How dangerous is this attack type (e.g., CEO Fraud is high severity)",
    ioc_quality: "Value of extracted IOCs (crypto wallets, IBANs are high value)",
    ioc_quantity: "Number of IOCs extracted from scammer messages",
    scammer_engagement:
        "How actively the scammer participated in the conversation",
    urgency_tactics:
        "Frequency of pressure tactics (urgent deadlines, threats, time limits)",
    personalization: "Level of specific targeting and personal details used",
};

/**
 * Weight percentages for each component (must sum to 100%)
 */
export const RISK_COMPONENT_WEIGHTS: Record<RiskComponentType, number> = {
    attack_severity: 25,
    ioc_quality: 20,
    ioc_quantity: 15,
    scammer_engagement: 15,
    urgency_tactics: 15,
    personalization: 10,
};

/**
 * Display order for risk components
 */
export const RISK_COMPONENT_ORDER: RiskComponentType[] = [
    "attack_severity",
    "ioc_quality",
    "ioc_quantity",
    "scammer_engagement",
    "urgency_tactics",
    "personalization",
];

/**
 * Get background color for component score bar
 * @param score - Raw score (0-10)
 */
export function getComponentScoreBg(score: number): string {
    if (score >= 8) return "bg-red-500";
    if (score >= 5) return "bg-orange-500";
    if (score >= 3) return "bg-yellow-500";
    return "bg-green-500";
}

/**
 * Map a numeric risk score (0-10) to a RiskLevel string.
 * Thresholds match getRiskScoreColor in ioc.ts: >=8 high, >=5 medium, else low.
 */
export function scoreToRiskLevel(score: number): RiskLevel {
    if (score >= 8) return "high";
    if (score >= 5) return "medium";
    return "low";
}

/**
 * Get text color class for risk level
 */
export function getRiskLevelColor(level: RiskLevel): string {
    switch (level) {
        case "high":
            return "text-red-500";
        case "medium":
            return "text-orange-500";
        case "low":
            return "text-green-500";
    }
}

/**
 * Get background color class for risk level
 */
export function getRiskLevelBg(level: RiskLevel): string {
    switch (level) {
        case "high":
            return "bg-red-500/10";
        case "medium":
            return "bg-orange-500/10";
        case "low":
            return "bg-green-500/10";
    }
}

/**
 * Get border color class for risk level
 */
export function getRiskLevelBorder(level: RiskLevel): string {
    switch (level) {
        case "high":
            return "border-red-500/40";
        case "medium":
            return "border-orange-500/40";
        case "low":
            return "border-green-500/40";
    }
}

/**
 * Get display label for risk level
 */
export function getRiskLevelLabel(level: RiskLevel): string {
    switch (level) {
        case "high":
            return "High Risk";
        case "medium":
            return "Medium Risk";
        case "low":
            return "Low Risk";
    }
}
