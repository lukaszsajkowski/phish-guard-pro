import { useState } from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { vi, describe, it, expect } from 'vitest';
import { EmailInput } from '../app/email-input';

/**
 * Wrapper component to test the controlled EmailInput
 * Manages state internally so tests can interact naturally
 */
function EmailInputWrapper({ onAnalyze }: { onAnalyze: (content: string) => Promise<void> }) {
    const [value, setValue] = useState('');
    return (
        <EmailInput
            value={value}
            onChange={setValue}
            onAnalyze={onAnalyze}
        />
    );
}

describe('EmailInput Component', () => {
    it('renders textarea with placeholder', () => {
        render(<EmailInputWrapper onAnalyze={async () => { }} />);
        const textarea = screen.getByPlaceholderText(/Paste phishing email content here/i);
        expect(textarea).toBeInTheDocument();
    });

    it('has Analyze button disabled initially', () => {
        render(<EmailInputWrapper onAnalyze={async () => { }} />);
        const button = screen.getByRole('button', { name: /Analyze/i });
        expect(button).toBeDisabled();
    });

    it('shows character counter', () => {
        render(<EmailInputWrapper onAnalyze={async () => { }} />);
        expect(screen.getByText('0 / 50,000')).toBeInTheDocument();
    });

    it('enables Analyze button when input is valid (10 chars)', async () => {
        render(<EmailInputWrapper onAnalyze={async () => { }} />);
        const textarea = screen.getByPlaceholderText(/Paste phishing email content here/i);
        const button = screen.getByRole('button', { name: /Analyze/i });

        await userEvent.type(textarea, '1234567890'); // 10 chars
        expect(button).toBeEnabled();
        expect(screen.getByText('10 / 50,000')).toBeInTheDocument();
    });

    it('shows validation warning and disables button when input is too short', async () => {
        render(<EmailInputWrapper onAnalyze={async () => { }} />);
        const textarea = screen.getByPlaceholderText(/Paste phishing email content here/i);
        const button = screen.getByRole('button', { name: /Analyze/i });

        await userEvent.type(textarea, 'short');
        expect(screen.getByText(/Email must be at least 10 characters/i)).toBeInTheDocument();
        expect(button).toBeDisabled();
    });

    it('calls onAnalyze callback when button is clicked', async () => {
        const mockAnalyze = vi.fn().mockResolvedValue(undefined);
        render(<EmailInputWrapper onAnalyze={mockAnalyze} />);

        const textarea = screen.getByPlaceholderText(/Paste phishing email content here/i);
        await userEvent.type(textarea, 'Valid email content for testing');

        const button = screen.getByRole('button', { name: /Analyze/i });
        await userEvent.click(button);

        expect(mockAnalyze).toHaveBeenCalledTimes(1);
        expect(mockAnalyze).toHaveBeenCalledWith('Valid email content for testing');
    });

    it('shows loading state during analysis', async () => {
        // Create a promise we can resolve manually to control timing
        let resolveAnalyze: () => void;
        const analyzePromise = new Promise<void>((resolve) => {
            resolveAnalyze = resolve;
        });
        const mockAnalyze = vi.fn().mockReturnValue(analyzePromise);

        render(<EmailInputWrapper onAnalyze={mockAnalyze} />);

        const textarea = screen.getByPlaceholderText(/Paste phishing email content here/i);
        await userEvent.type(textarea, 'Valid email content');

        const button = screen.getByRole('button', { name: /Analyze/i });
        await userEvent.click(button);

        // Should show loading state
        expect(screen.getByText(/Analyzing.../i)).toBeInTheDocument();
        expect(button).toBeDisabled();
        expect(textarea).toBeDisabled();

        // Finish analysis
        resolveAnalyze!();

        // Wait for loading state to finish
        await waitFor(() => {
            expect(screen.getByRole('button', { name: /Analyze/i })).toBeEnabled();
            expect(screen.queryByText(/Analyzing.../i)).not.toBeInTheDocument();
        });
    });

    it('validates maximum length', async () => {
        render(<EmailInputWrapper onAnalyze={async () => { }} />);
        const textarea = screen.getByPlaceholderText(/Paste phishing email content here/i);

        // Use fireEvent for instant large text changes to speed up test
        const longText = 'a'.repeat(50001);
        fireEvent.change(textarea, { target: { value: longText } });

        expect(screen.getByText(/Email must not exceed 50,000 characters/i)).toBeInTheDocument();
        expect(screen.getByRole('button', { name: /Analyze/i })).toBeDisabled();
    });
});
