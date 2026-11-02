import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { ClassificationResult } from '../ClassificationResult';

const base = { attackType: 'ceo_fraud' as const, reasoning: 'r' };

describe('ClassificationResult decision source badge', () => {
    it('renders Basal for basal', () => {
        render(<ClassificationResult {...base} confidence={90} decisionSource="basal" />);
        expect(screen.getByTestId('decision-source')).toHaveTextContent('Basal');
    });

    it('renders GPT-4o for llm', () => {
        render(<ClassificationResult {...base} confidence={90} decisionSource="llm" />);
        expect(screen.getByTestId('decision-source')).toHaveTextContent('GPT-4o');
    });

    it('renders low confidence label', () => {
        render(<ClassificationResult {...base} confidence={90} decisionSource="basal_low_confidence" />);
        expect(screen.getByTestId('decision-source')).toHaveTextContent('Basal (low confidence)');
    });

    it('renders no badge when prop omitted', () => {
        render(<ClassificationResult {...base} confidence={90} />);
        expect(screen.queryByTestId('decision-source')).not.toBeInTheDocument();
    });
});

describe('ClassificationResult confidence styling', () => {
    it.each([
        [20, 'bg-yellow-100'],
        [49.9, 'bg-yellow-100'],
        [50, 'bg-blue-100'],
        [79.9, 'bg-blue-100'],
        [80, 'bg-green-100'],
    ])('confidence %s uses %s', (confidence, cls) => {
        render(<ClassificationResult {...base} confidence={confidence} />);
        expect(screen.getByText(/% Confidence/)).toHaveClass(cls);
    });
});
