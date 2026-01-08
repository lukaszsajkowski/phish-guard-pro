"use client"

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { AlertCircle, CheckCircle2 } from "lucide-react"

export type AttackType =
    | "nigerian_419"
    | "ceo_fraud"
    | "fake_invoice"
    | "romance_scam"
    | "tech_support"
    | "lottery_prize"
    | "crypto_investment"
    | "delivery_scam"
    | "not_phishing"

export interface ClassificationResultProps {
    attackType: AttackType
    confidence: number
    reasoning: string
}

const ATTACK_TYPE_LABELS: Record<AttackType, string> = {
    nigerian_419: "Nigerian 419",
    ceo_fraud: "CEO Fraud",
    fake_invoice: "Fake Invoice",
    romance_scam: "Romance Scam",
    tech_support: "Tech Support",
    lottery_prize: "Lottery/Prize",
    crypto_investment: "Crypto Investment",
    delivery_scam: "Delivery Scam",
    not_phishing: "Not Phishing",
}

export function ClassificationResult({ attackType, confidence, reasoning }: ClassificationResultProps) {
    const isPhishing = attackType !== "not_phishing"
    const isLowConfidence = confidence < 30
    const isHighConfidence = confidence >= 80

    return (
        <div className="space-y-4" data-testid="classification-result">
            <Card className={isPhishing ? "border-red-200 bg-red-50/10" : "border-green-200 bg-green-50/10"}>
                <CardHeader>
                    <div className="flex items-center justify-between">
                        <CardTitle className="text-lg font-semibold flex items-center gap-2">
                            {isPhishing ? (
                                <AlertCircle className="h-5 w-5 text-red-500" />
                            ) : (
                                <CheckCircle2 className="h-5 w-5 text-green-500" />
                            )}
                            {ATTACK_TYPE_LABELS[attackType]}
                        </CardTitle>
                        <span className={`text-sm font-medium px-2 py-1 rounded-full ${isHighConfidence ? "bg-green-100 text-green-700" :
                            confidence < 50 ? "bg-yellow-100 text-yellow-700" : "bg-blue-100 text-blue-700"
                            }`}>
                            {confidence.toFixed(1)}% Confidence
                        </span>
                    </div>
                    <CardDescription>
                        {isPhishing ? "Phishing Attack Detected" : "Legitimate Email Detected"}
                    </CardDescription>
                </CardHeader>
                <CardContent>
                    <p className="text-sm text-muted-foreground">{reasoning}</p>
                </CardContent>
            </Card>

            {!isPhishing && isLowConfidence && (
                <Alert variant="warning">
                    <AlertCircle className="h-4 w-4" />
                    <AlertTitle>Uncertain Classification</AlertTitle>
                    <AlertDescription>
                        The system is not confident this is a legitimate email. Please review manually.
                    </AlertDescription>
                </Alert>
            )}
        </div>
    )
}
