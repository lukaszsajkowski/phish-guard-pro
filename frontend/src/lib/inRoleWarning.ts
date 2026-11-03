import type { ChatMessage, InRoleWarning } from "@/types/schemas";

/**
 * Return a new array where the message with `messageId` carries `warning`
 * (null clears an existing one). All other messages keep their identity.
 */
export function applyInRoleWarning(
    messages: ChatMessage[],
    messageId: string,
    warning: InRoleWarning | null
): ChatMessage[] {
    return messages.map((msg) =>
        msg.id === messageId ? { ...msg, inRoleWarning: warning } : msg
    );
}
