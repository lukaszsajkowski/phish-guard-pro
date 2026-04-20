/**
 * Database types for PhishGuard Pro
 * Auto-generated from Supabase schema
 */

export type AttackType =
    | "nigerian_419"
    | "ceo_fraud"
    | "fake_invoice"
    | "romance_scam"
    | "tech_support"
    | "lottery_prize"
    | "crypto_investment"
    | "delivery_scam"
    | "not_phishing";

export type SessionStatus = "active" | "archived";

export type MessageRole = "user" | "assistant" | "scammer";

export type IocType = "iban" | "btc" | "url" | "phone" | "ip";

export interface Persona {
    name: string;
    age: number;
    style: string;
    phrases: string[];
}

export interface Database {
    public: {
        Tables: {
            sessions: {
                Row: {
                    id: string;
                    user_id: string;
                    title: string | null;
                    attack_type: AttackType | null;
                    persona: Persona | null;
                    status: SessionStatus;
                    created_at: string;
                };
                Insert: {
                    id?: string;
                    user_id: string;
                    title?: string | null;
                    attack_type?: AttackType | null;
                    persona?: Persona | null;
                    status?: SessionStatus;
                    created_at?: string;
                };
                Update: {
                    id?: string;
                    user_id?: string;
                    title?: string | null;
                    attack_type?: AttackType | null;
                    persona?: Persona | null;
                    status?: SessionStatus;
                    created_at?: string;
                };
            };
            messages: {
                Row: {
                    id: string;
                    session_id: string;
                    role: MessageRole;
                    content: string;
                    metadata: Record<string, unknown> | null;
                    created_at: string;
                };
                Insert: {
                    id?: string;
                    session_id: string;
                    role: MessageRole;
                    content: string;
                    metadata?: Record<string, unknown> | null;
                    created_at?: string;
                };
                Update: {
                    id?: string;
                    session_id?: string;
                    role?: MessageRole;
                    content?: string;
                    metadata?: Record<string, unknown> | null;
                    created_at?: string;
                };
            };
            ioc_extracted: {
                Row: {
                    id: string;
                    session_id: string;
                    type: IocType;
                    value: string;
                    confidence: number;
                    created_at: string;
                };
                Insert: {
                    id?: string;
                    session_id: string;
                    type: IocType;
                    value: string;
                    confidence: number;
                    created_at?: string;
                };
                Update: {
                    id?: string;
                    session_id?: string;
                    type?: IocType;
                    value?: string;
                    confidence?: number;
                    created_at?: string;
                };
            };
        };
        Views: Record<string, never>;
        Functions: Record<string, never>;
    };
}
