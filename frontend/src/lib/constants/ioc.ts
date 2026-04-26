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
export const ATTACK_TYPE_COLORS: Record<string, string> = {
  nigerian_419: "bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-400",
  ceo_fraud: "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400",
  fake_invoice: "bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400",
  romance_scam: "bg-pink-100 text-pink-700 dark:bg-pink-900/30 dark:text-pink-400",
  tech_support: "bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-400",
  lottery_prize: "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400",
  crypto_investment: "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400",
  delivery_scam: "bg-teal-100 text-teal-700 dark:bg-teal-900/30 dark:text-teal-400",
  not_phishing: "bg-gray-100 text-gray-700 dark:bg-gray-900/30 dark:text-gray-400",
};

export function getRiskScoreColor(score: number): string {
  if (score >= 7) {
    return "text-red-500 dark:text-red-400";
  } else if (score >= 4) {
    return "text-orange-500 dark:text-orange-400";
  }
  return "text-green-500 dark:text-green-400";
}

/**
 * Get background color class for risk score progress bar
 * Returns Tailwind CSS background color class based on risk score (0-10)
 *
 * @param score - Risk score from 0 to 10
 * @returns Tailwind CSS background color class
 */
export function getRiskScoreBarColor(score: number): string {
  if (score >= 7) {
    return "bg-red-500";
  } else if (score >= 4) {
    return "bg-orange-500";
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
  if (score >= 7) {
    return "bg-red-50";
  } else if (score >= 4) {
    return "bg-orange-50";
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
  if (score >= 7) {
    return "High";
  } else if (score >= 4) {
    return "Medium";
  }
  return "Low";
}
