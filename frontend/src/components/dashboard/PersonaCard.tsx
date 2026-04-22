import { Persona } from "@/types/schemas";

interface PersonaCardProps {
    persona: Persona;
}

export function PersonaCard({ persona }: PersonaCardProps) {
    const formatPersonaType = (type: string) => {
        return type
            .split("_")
            .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
            .join(" ");
    };

    return (
        <div
            className="bg-surface border border-border2 rounded-lg overflow-hidden"
            data-testid="persona-card"
        >
            {/* Header */}
            <div className="flex items-start justify-between gap-3 px-5 pt-[18px] pb-4 border-b border-border">
                <div className="flex items-center gap-2.5">
                    {/* Blue circle avatar */}
                    <div className="w-9 h-9 rounded-full bg-pg-blue-dim border border-pg-blue flex items-center justify-center shrink-0">
                        <svg
                            viewBox="0 0 16 16"
                            fill="none"
                            stroke="currentColor"
                            strokeWidth="1.5"
                            className="w-4 h-4 text-pg-blue"
                        >
                            <circle cx="8" cy="5" r="3" />
                            <path d="M2 14c0-3 2.7-5 6-5s6 2 6 5" />
                        </svg>
                    </div>
                    <div>
                        <div className="text-[17px] font-semibold tracking-[-0.02em] text-text">
                            {persona.name}
                        </div>
                        <div className="text-[12px] text-text-muted mt-px">
                            {formatPersonaType(persona.persona_type)}
                        </div>
                    </div>
                </div>
                {/* Age badge */}
                <span className="px-2.5 py-1 bg-surface2 border border-border2 rounded-full text-[12px] font-medium text-text-secondary whitespace-nowrap">
                    {persona.age} years old
                </span>
            </div>

            {/* Body — 2-column grid */}
            <div className="grid grid-cols-2">
                {/* Background */}
                <div className="px-5 py-4 border-r border-border">
                    <div className="flex items-center gap-1.5 text-[11px] font-semibold tracking-[0.08em] uppercase text-text-muted mb-2">
                        <svg
                            viewBox="0 0 16 16"
                            fill="none"
                            stroke="currentColor"
                            strokeWidth="1.5"
                            className="w-3 h-3"
                        >
                            <path d="M2 4h12v8a1 1 0 0 1-1 1H3a1 1 0 0 1-1-1V4z" />
                            <line x1="2" y1="4" x2="14" y2="4" />
                        </svg>
                        Background
                    </div>
                    <p className="text-[13px] text-text-secondary leading-relaxed">
                        {persona.background}
                    </p>
                </div>

                {/* Communication Style */}
                <div className="px-5 py-4">
                    <div className="flex items-center gap-1.5 text-[11px] font-semibold tracking-[0.08em] uppercase text-text-muted mb-2">
                        <svg
                            viewBox="0 0 16 16"
                            fill="none"
                            stroke="currentColor"
                            strokeWidth="1.5"
                            className="w-3 h-3"
                        >
                            <path d="M4 12V8a4 4 0 0 1 8 0v4" />
                            <path d="M2 12h12" />
                        </svg>
                        Communication Style
                    </div>
                    <p className="text-[13px] text-text-secondary leading-relaxed italic pl-3 border-l-2 border-border2">
                        {persona.style_description}
                    </p>
                </div>
            </div>
        </div>
    );
}
