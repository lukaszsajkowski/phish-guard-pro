import { describe, it, expect } from "vitest";
import { applyInRoleWarning } from "../inRoleWarning";
import type { ChatMessage, InRoleWarning } from "@/types/schemas";

const warning: InRoleWarning = { message: "May break role.", confidence: 0.87 };

const msg = (id: string, extra: Partial<ChatMessage> = {}): ChatMessage => ({
    id,
    sender: "bot",
    content: `content ${id}`,
    timestamp: new Date(0),
    ...extra,
});

describe("applyInRoleWarning", () => {
    it("applies the warning to the target message", () => {
        const result = applyInRoleWarning([msg("a"), msg("b")], "b", warning);
        expect(result[1].inRoleWarning).toEqual(warning);
        expect(result[0].inRoleWarning).toBeUndefined();
    });

    it("clears an existing warning with null", () => {
        const result = applyInRoleWarning([msg("a", { inRoleWarning: warning })], "a", null);
        expect(result[0].inRoleWarning).toBeNull();
    });

    it("leaves other messages as the same objects", () => {
        const a = msg("a");
        const b = msg("b");
        const c = msg("c");
        const result = applyInRoleWarning([a, b, c], "b", warning);
        expect(result[0]).toBe(a);
        expect(result[2]).toBe(c);
        expect(result[1]).not.toBe(b);
        expect(b.inRoleWarning).toBeUndefined();
    });

    it("keeps array content unchanged for an unknown id", () => {
        const input = [msg("a"), msg("b")];
        const result = applyInRoleWarning(input, "zzz", warning);
        expect(result).toEqual(input);
        result.forEach((m, i) => expect(m).toBe(input[i]));
    });
});
