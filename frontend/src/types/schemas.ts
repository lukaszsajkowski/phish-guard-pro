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
    session_id?: string;
}

export interface AgentThinking {
    turn_goal: string;
    selected_tactic: string;
    reasoning: string;
}

export interface ResponseGenerationResult {
    content: string;
    generation_time_ms: number;
    safety_validated: boolean;
    regeneration_count: number;
    used_fallback_model: boolean;
    thinking?: AgentThinking;
    message_id: string;
}

export interface ChatMessage {
    id: string;
    sender: "bot" | "scammer";
    content: string;
    timestamp: Date;
    thinking?: AgentThinking;
}

