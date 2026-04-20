import {
  Landmark,
  Bitcoin,
  Link,
  Phone,
  Globe,
  type LucideIcon,
} from "lucide-react";

/**
 * IOC Type to Icon mapping
 * Maps IOC types to their corresponding Lucide icon components
 */
export const IOC_ICONS: Record<string, LucideIcon> = {
  iban: Landmark,
  btc: Bitcoin,
  url: Link,
  phone: Phone,
  ip: Globe,
};

/**
 * IOC Type to Display Label mapping
 * Maps IOC types to human-readable labels
 */
export const IOC_LABELS: Record<string, string> = {
  iban: "Bank Account (IBAN)",
  btc: "Bitcoin Address",
  url: "URL",
  phone: "Phone Number",
  ip: "IP Address",
};

/**
 * Attack Type to Display Label mapping
 * Maps attack types to human-readable labels
 */
export const ATTACK_TYPE_LABELS: Record<string, string> = {
  nigerian_419: "Nigerian 419 Scam",
  ceo_fraud: "CEO Fraud / BEC",
  fake_invoice: "Fake Invoice",
  romance_scam: "Romance Scam",
  tech_support: "Tech Support Scam",
  lottery_prize: "Lottery/Prize Scam",
  crypto_investment: "Crypto Investment Scam",
  delivery_scam: "Delivery Scam",
  not_phishing: "Not Phishing",
};

/**
 * Get color class for risk score
 * Returns Tailwind CSS color class based on risk score (0-10)
 *
 * @param score - Risk score from 0 to 10
 * @returns Tailwind CSS color class
 */
export function getRiskScoreColor(score: number): string {
  if (score >= 8) {
    return "text-red-500";
  } else if (score >= 5) {
    return "text-orange-500";
  } else if (score >= 3) {
    return "text-yellow-500";
  }
  return "text-green-500";
}

/**
 * Get background color class for risk score progress bar
 * Returns Tailwind CSS background color class based on risk score (0-10)
 *
 * @param score - Risk score from 0 to 10
 * @returns Tailwind CSS background color class
 */
export function getRiskScoreBarColor(score: number): string {
  if (score >= 8) {
    return "bg-red-500";
  } else if (score >= 5) {
    return "bg-orange-500";
  } else if (score >= 3) {
    return "bg-yellow-500";
  }
  return "bg-green-500";
}

/**
 * Get background color class for risk score display
 * Returns Tailwind CSS background color class based on risk score (0-10)
 *
 * @param score - Risk score from 0 to 10
 * @returns Tailwind CSS background color class
 */
export function getRiskScoreBg(score: number): string {
  if (score >= 8) {
    return "bg-red-50";
  } else if (score >= 5) {
    return "bg-orange-50";
  } else if (score >= 3) {
    return "bg-yellow-50";
  }
  return "bg-green-50";
}

/**
 * Get risk level label based on score
 * Returns a human-readable risk level (Low, Medium, High)
 *
 * @param score - Risk score from 0 to 10
 * @returns Risk level label
 */
export function getRiskLabel(score: number): string {
  if (score >= 8) {
    return "High";
  } else if (score >= 5) {
    return "Medium";
  }
  return "Low";
}
