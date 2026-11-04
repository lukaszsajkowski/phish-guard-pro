import { describe, it, expect } from 'vitest';
import { ATTACK_TYPE_COLORS, ATTACK_TYPE_LABELS } from '../ioc';

describe('attack type constants', () => {
    it('label and color credential_phishing', () => {
        expect(ATTACK_TYPE_LABELS.credential_phishing).toBe('Credential Phishing');
        expect(ATTACK_TYPE_COLORS.credential_phishing).toContain('bg-indigo-100');
    });
});
