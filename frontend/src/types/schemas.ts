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

export interface ExtractedIOC {
    id?: string;
    type: "btc" | "btc_wallet" | "iban" | "phone" | "url";
    value: string;
    context?: string;
    is_high_value: boolean;
    created_at?: string;
}

export interface TimelineEvent {
    timestamp: string;
    event_type: "ioc_extracted" | "message_received";
    description: string;
    ioc_id?: string;
    is_high_value?: boolean;
}

export interface IntelDashboardData {
    session_id: string;
    attack_type: string;
    confidence: number;
    iocs: ExtractedIOC[];
    total_iocs: number;
    high_value_count: number;
    risk_score: number;
    timeline: TimelineEvent[];
}
