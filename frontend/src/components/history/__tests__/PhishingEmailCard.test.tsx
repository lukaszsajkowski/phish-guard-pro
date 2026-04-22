import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { PhishingEmailCard } from '../PhishingEmailCard';

describe('PhishingEmailCard Component', () => {
    const shortEmail = 'Dear Beneficiary,\n\nI am Barrister James Okonkwo.';

    const longEmail = [
        'Dear Beneficiary,',
        'I am Barrister James Okonkwo, legal counsel to the late Chief Michael Williams.',
        'After thorough investigation, I discovered you share the same surname.',
        'To proceed, I require your full name, date of birth, address, and phone number.',
        'God bless you,\nBarrister James Okonkwo',
    ].join('\n\n');

    describe('Rendering', () => {
        it('renders the card with email content', () => {
            render(<PhishingEmailCard emailContent={shortEmail} />);

            expect(screen.getByTestId('phishing-email-card')).toBeInTheDocument();
            expect(screen.getByTestId('email-body')).toHaveTextContent('Dear Beneficiary,');
        });

        it('renders section title', () => {
            render(<PhishingEmailCard emailContent={shortEmail} />);

            expect(screen.getByText('Original Phishing Email')).toBeInTheDocument();
        });

        it('renders subject when provided', () => {
            render(
                <PhishingEmailCard
                    emailContent={shortEmail}
                    subject="URGENT: Inheritance Funds Transfer"
                />
            );

            expect(screen.getByTestId('email-subject')).toHaveTextContent(
                'URGENT: Inheritance Funds Transfer'
            );
        });

        it('renders from/to when provided', () => {
            render(
                <PhishingEmailCard
                    emailContent={shortEmail}
                    from="scammer@example.com"
                    to="victim@example.com"
                />
            );

            expect(screen.getByText(/From: scammer@example.com/)).toBeInTheDocument();
            expect(screen.getByText(/To: victim@example.com/)).toBeInTheDocument();
        });
    });

    describe('Expand/Collapse', () => {
        it('does not show toggle for short emails', () => {
            render(<PhishingEmailCard emailContent={shortEmail} />);

            expect(screen.queryByTestId('email-expand-toggle')).not.toBeInTheDocument();
        });

        it('shows toggle for long emails', () => {
            render(<PhishingEmailCard emailContent={longEmail} />);

            expect(screen.getByTestId('email-expand-toggle')).toBeInTheDocument();
            expect(screen.getByText('Show full email')).toBeInTheDocument();
        });

        it('expands email on toggle click', () => {
            render(<PhishingEmailCard emailContent={longEmail} />);

            const toggle = screen.getByTestId('email-expand-toggle');
            fireEvent.click(toggle);

            expect(screen.getByText('Show less')).toBeInTheDocument();
            // Full content should now be visible
            expect(screen.getByTestId('email-body')).toHaveTextContent('God bless you,');
        });

        it('collapses email on second toggle click', () => {
            render(<PhishingEmailCard emailContent={longEmail} />);

            const toggle = screen.getByTestId('email-expand-toggle');
            fireEvent.click(toggle); // expand
            fireEvent.click(toggle); // collapse

            expect(screen.getByText('Show full email')).toBeInTheDocument();
        });
    });
});
