export interface Persona {
    persona_type: string;
    name: string;
    age: number;
    style_description: string;
    background: string;
}

export interface ClassificationResponse {
    attack_type: string;
    confidence: number;
    reasoning: string;
    classification_time_ms: number;
    persona?: Persona;
}
