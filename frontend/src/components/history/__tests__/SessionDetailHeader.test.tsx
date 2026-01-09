import { render, screen } from '@testing-library/react';
import { vi, describe, it, expect, beforeEach } from 'vitest';
import { SessionDetailHeader } from '../SessionDetailHeader';

// Mock date-fns format function for consistent test results
vi.mock('date-fns', () => ({
    format: vi.fn((date: Date, formatStr: string) => {
        // Return a consistent formatted date for testing
        return 'Jan 15, 2024, 10:30 AM';
    }),
}));

// Mock next/link
vi.mock('next/link', () => ({
    default: ({ children, href, ...props }: { children: React.ReactNode; href: string }) => (
        <a href={href} {...props}>{children}</a>
    ),
}));

describe('SessionDetailHeader Component', () => {
    const defaultProps = {
        attackType: 'nigerian_419',
        attackTypeDisplay: 'Nigerian 419 Scam',
        createdAt: '2024-01-15T10:30:00Z',
        status: 'active',
        turnCount: 5,
    };

    beforeEach(() => {
        vi.clearAllMocks();
    });

    describe('Rendering', () => {
        it('renders with all props correctly', () => {
            render(<SessionDetailHeader {...defaultProps} />);

            expect(screen.getByTestId('session-detail-header')).toBeInTheDocument();
            expect(screen.getByTestId('attack-type-badge')).toHaveTextContent('Nigerian 419 Scam');
            expect(screen.getByTestId('status-badge')).toHaveTextContent('Active');
            expect(screen.getByTestId('turn-count')).toHaveTextContent('5 turns');
            expect(screen.getByTestId('created-at')).toBeInTheDocument();
        });

        it('renders back to history link with correct href', () => {
            render(<SessionDetailHeader {...defaultProps} />);

            const backLink = screen.getByTestId('back-to-history-link');
            expect(backLink).toBeInTheDocument();
            expect(backLink).toHaveAttribute('href', '/history');
            expect(backLink).toHaveTextContent('Back to history');
        });

        it('renders attack type display text', () => {
            render(<SessionDetailHeader {...defaultProps} attackTypeDisplay="CEO Fraud" />);

            expect(screen.getByTestId('attack-type-badge')).toHaveTextContent('CEO Fraud');
        });
    });

    describe('Attack Type Badge Colors', () => {
        const attackTypeTestCases = [
            { attackType: 'nigerian_419', display: 'Nigerian 419', expectedColorClass: 'bg-orange-100' },
            { attackType: 'ceo_fraud', display: 'CEO Fraud', expectedColorClass: 'bg-red-100' },
            { attackType: 'fake_invoice', display: 'Fake Invoice', expectedColorClass: 'bg-yellow-100' },
            { attackType: 'romance_scam', display: 'Romance Scam', expectedColorClass: 'bg-pink-100' },
            { attackType: 'tech_support', display: 'Tech Support', expectedColorClass: 'bg-purple-100' },
            { attackType: 'lottery_prize', display: 'Lottery Prize', expectedColorClass: 'bg-green-100' },
            { attackType: 'crypto_investment', display: 'Crypto Investment', expectedColorClass: 'bg-blue-100' },
            { attackType: 'delivery_scam', display: 'Delivery Scam', expectedColorClass: 'bg-teal-100' },
            { attackType: 'not_phishing', display: 'Not Phishing', expectedColorClass: 'bg-gray-100' },
        ];

        it.each(attackTypeTestCases)(
            'renders $display badge with correct color class',
            ({ attackType, display, expectedColorClass }) => {
                render(
                    <SessionDetailHeader
                        {...defaultProps}
                        attackType={attackType}
                        attackTypeDisplay={display}
                    />
                );

                const badge = screen.getByTestId('attack-type-badge');
                expect(badge).toHaveTextContent(display);
                expect(badge.className).toContain(expectedColorClass);
            }
        );

        it('falls back to not_phishing colors for unknown attack type', () => {
            render(
                <SessionDetailHeader
                    {...defaultProps}
                    attackType="unknown_type"
                    attackTypeDisplay="Unknown"
                />
            );

            const badge = screen.getByTestId('attack-type-badge');
            expect(badge.className).toContain('bg-gray-100');
        });
    });

    describe('Status Badge Colors', () => {
        it('renders active status with green color', () => {
            render(<SessionDetailHeader {...defaultProps} status="active" />);

            const badge = screen.getByTestId('status-badge');
            expect(badge).toHaveTextContent('Active');
            expect(badge.className).toContain('bg-green-100');
        });

        it('renders archived status with gray color', () => {
            render(<SessionDetailHeader {...defaultProps} status="archived" />);

            const badge = screen.getByTestId('status-badge');
            expect(badge).toHaveTextContent('Archived');
            expect(badge.className).toContain('bg-gray-100');
        });

        it('renders completed status with blue color', () => {
            render(<SessionDetailHeader {...defaultProps} status="completed" />);

            const badge = screen.getByTestId('status-badge');
            expect(badge).toHaveTextContent('Completed');
            expect(badge.className).toContain('bg-blue-100');
        });

        it('falls back to archived colors for unknown status', () => {
            render(<SessionDetailHeader {...defaultProps} status="unknown_status" />);

            const badge = screen.getByTestId('status-badge');
            expect(badge.className).toContain('bg-gray-100');
        });
    });

    describe('Date Formatting', () => {
        it('formats valid date string correctly', () => {
            render(<SessionDetailHeader {...defaultProps} createdAt="2024-01-15T10:30:00Z" />);

            // Should show the mocked formatted date
            expect(screen.getByTestId('created-at')).toHaveTextContent('Jan 15, 2024, 10:30 AM');
        });

        it('shows Unknown date for invalid date string', async () => {
            // Reset mock to throw error for invalid dates
            const dateFns = await import('date-fns');
            vi.mocked(dateFns.format).mockImplementationOnce(() => {
                throw new Error('Invalid date');
            });

            render(<SessionDetailHeader {...defaultProps} createdAt="invalid-date" />);

            expect(screen.getByTestId('created-at')).toHaveTextContent('Unknown date');
        });
    });

    describe('Turn Count Display', () => {
        it('renders singular turn for count of 1', () => {
            render(<SessionDetailHeader {...defaultProps} turnCount={1} />);

            expect(screen.getByTestId('turn-count')).toHaveTextContent('1 turn');
        });

        it('renders plural turns for count greater than 1', () => {
            render(<SessionDetailHeader {...defaultProps} turnCount={5} />);

            expect(screen.getByTestId('turn-count')).toHaveTextContent('5 turns');
        });

        it('renders plural turns for count of 0', () => {
            render(<SessionDetailHeader {...defaultProps} turnCount={0} />);

            expect(screen.getByTestId('turn-count')).toHaveTextContent('0 turns');
        });

        it('renders correct turn count for large numbers', () => {
            render(<SessionDetailHeader {...defaultProps} turnCount={100} />);

            expect(screen.getByTestId('turn-count')).toHaveTextContent('100 turns');
        });
    });

    describe('Status Formatting', () => {
        it('capitalizes first letter of status', () => {
            render(<SessionDetailHeader {...defaultProps} status="active" />);

            expect(screen.getByTestId('status-badge')).toHaveTextContent('Active');
        });

        it('handles already capitalized status', () => {
            render(<SessionDetailHeader {...defaultProps} status="Active" />);

            expect(screen.getByTestId('status-badge')).toHaveTextContent('Active');
        });

        it('handles uppercase status', () => {
            render(<SessionDetailHeader {...defaultProps} status="COMPLETED" />);

            // formatStatus capitalizes first letter, rest stays as is
            expect(screen.getByTestId('status-badge')).toHaveTextContent('COMPLETED');
        });
    });
});
