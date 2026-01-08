import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { User, Dna, FileText } from "lucide-react";
import { Persona } from "@/types/schemas";

interface PersonaCardProps {
    persona: Persona;
}

export function PersonaCard({ persona }: PersonaCardProps) {
    // Format the persona type for display (e.g., "naive_retiree" -> "Naive Retiree")
    // Or assume the backend sends it as enum value string, handle display nicely.
    // The backend sends snake_case. 
    // Let's rely on the display name if possible, but the model has `persona_type` correctly.
    // We can format it here.
    const formatPersonaType = (type: string) => {
        return type.split('_').map(word => word.charAt(0).toUpperCase() + word.slice(1)).join(' ');
    };

    return (
        <Card className="w-full border-blue-200 bg-blue-50/10" data-testid="persona-card">
            <CardHeader>
                <div className="flex items-center justify-between">
                    <CardTitle className="text-lg font-semibold flex items-center gap-2">
                        <User className="h-5 w-5 text-blue-500" />
                        {persona.name}
                    </CardTitle>
                    <span className="text-sm font-medium px-2 py-1 rounded-full bg-blue-100 text-blue-700">
                        {persona.age} years old
                    </span>
                </div>
                <CardDescription>{formatPersonaType(persona.persona_type)}</CardDescription>
            </CardHeader>
            <CardContent className="space-y-3 text-sm">
                <div>
                    <div className="flex items-center gap-2 text-muted-foreground mb-1">
                        <FileText className="h-4 w-4" />
                        <span className="font-medium">Background</span>
                    </div>
                    <p className="pl-6 text-muted-foreground">
                        {persona.background}
                    </p>
                </div>

                <div>
                    <div className="flex items-center gap-2 text-muted-foreground mb-1">
                        <Dna className="h-4 w-4" />
                        <span className="font-medium">Communication Style</span>
                    </div>
                    <p className="pl-6 text-muted-foreground italic">
                        "{persona.style_description}"
                    </p>
                </div>
            </CardContent>
        </Card>
    );
}
