"use client";

import Link from "next/link";
import { Shield } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";

export function EmptyState() {
    return (
        <Card className="w-full max-w-md mx-auto" data-testid="empty-state">
            <CardContent className="flex flex-col items-center justify-center py-12 text-center">
                <div className="rounded-full bg-muted p-4 mb-4">
                    <Shield className="h-10 w-10 text-muted-foreground" />
                </div>
                <h3 className="text-lg font-semibold mb-2">No sessions yet</h3>
                <p className="text-sm text-muted-foreground mb-6 max-w-xs">
                    You haven&apos;t analyzed any phishing emails yet. Start your first session to begin collecting threat intelligence.
                </p>
                <Button asChild>
                    <Link href="/dashboard">Start analyzing</Link>
                </Button>
            </CardContent>
        </Card>
    );
}
