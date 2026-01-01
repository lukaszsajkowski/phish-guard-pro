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
        <Card className="w-full mt-4 border-l-4 border-l-blue-500 animate-in fade-in slide-in-from-bottom-4 duration-500 delay-150">
            <CardHeader className="pb-2">
                <div className="flex items-center gap-2 mb-1">
                    <User className="h-5 w-5 text-blue-500" />
                    <span className="text-sm font-medium text-blue-500">Suggested Persona</span>
                </div>
                <CardTitle className="text-xl flex items-center justify-between">
                    {persona.name}
                    <span className="text-sm font-normal text-muted-foreground bg-muted px-2 py-1 rounded-full">
                        {persona.age} years old
                    </span>
                </CardTitle>
                <CardDescription>{formatPersonaType(persona.persona_type)}</CardDescription>
            </CardHeader>
            <CardContent className="grid gap-4 text-sm mt-2">
                <div className="grid gap-1">
                    <div className="flex items-center gap-2 text-muted-foreground mb-1">
                        <FileText className="h-4 w-4" />
                        <span className="font-medium">Background</span>
                    </div>
                    <p className="pl-6 text-foreground/90 leading-relaxed">
                        {persona.background}
                    </p>
                </div>

                <div className="grid gap-1">
                    <div className="flex items-center gap-2 text-muted-foreground mb-1">
                        <Dna className="h-4 w-4" />
                        <span className="font-medium">Communication Style</span>
                    </div>
                    <p className="pl-6 text-foreground/90 leading-relaxed italic">
                        "{persona.style_description}"
                    </p>
                </div>
            </CardContent>
        </Card>
    );
}
