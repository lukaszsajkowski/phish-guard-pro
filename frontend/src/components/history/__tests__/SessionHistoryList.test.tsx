import { render, screen, fireEvent } from '@testing-library/react';
import { vi, describe, it, expect, beforeEach } from 'vitest';
import { SessionHistoryList } from '../SessionHistoryList';
import { SessionHistoryItem } from '@/types/schemas';

// Mock date-fns to ensure consistent test results
vi.mock('date-fns', () => ({
    formatDistanceToNow: vi.fn((date: Date) => {
        // Return a consistent value for testing
        return '2 days ago';
    }),
}));

describe('SessionHistoryList Component', () => {
    const mockOnSessionClick = vi.fn();

    beforeEach(() => {
        mockOnSessionClick.mockClear();
    });

    const createMockSession = (overrides: Partial<SessionHistoryItem> = {}): SessionHistoryItem => ({
        session_id: 'test-session-123',
        title: null,
        attack_type: 'nigerian_419',
        attack_type_display: 'Nigerian 419',
        persona_name: 'Margaret Thompson',
        turn_count: 5,
        created_at: '2024-01-15T10:30:00Z',
        risk_score: 8,
        status: 'active',
        ...overrides,
    });

    describe('Rendering', () => {
        it('renders session list with mock data', () => {
            const sessions: SessionHistoryItem[] = [
                createMockSession({ session_id: 'session-1' }),
                createMockSession({ session_id: 'session-2', attack_type: 'ceo_fraud', attack_type_display: 'CEO Fraud' }),
            ];

            render(<SessionHistoryList sessions={sessions} onSessionClick={mockOnSessionClick} />);

            expect(screen.getByTestId('session-history-list')).toBeInTheDocument();
            expect(screen.getByTestId('session-row-session-1')).toBeInTheDocument();
            expect(screen.getByTestId('session-row-session-2')).toBeInTheDocument();
        });

        it('renders attack type display correctly', () => {
            const sessions: SessionHistoryItem[] = [
                createMockSession({ attack_type_display: 'Nigerian 419' }),
            ];

            render(<SessionHistoryList sessions={sessions} onSessionClick={mockOnSessionClick} />);

            expect(screen.getByText('Nigerian 419')).toBeInTheDocument();
        });

        it('renders persona name when provided', () => {
            const sessions: SessionHistoryItem[] = [
                createMockSession({ persona_name: 'Robert Chen' }),
            ];

            render(<SessionHistoryList sessions={sessions} onSessionClick={mockOnSessionClick} />);

            expect(screen.getByText('Robert Chen')).toBeInTheDocument();
        });

        it('does not render persona name section when null', () => {
            const sessions: SessionHistoryItem[] = [
                createMockSession({ persona_name: null }),
            ];

            render(<SessionHistoryList sessions={sessions} onSessionClick={mockOnSessionClick} />);

            // Persona name should not be present
            expect(screen.queryByText('Margaret Thompson')).not.toBeInTheDocument();
        });

        it('renders turn count correctly', () => {
            const sessions: SessionHistoryItem[] = [
                createMockSession({ turn_count: 5 }),
            ];

            render(<SessionHistoryList sessions={sessions} onSessionClick={mockOnSessionClick} />);

            expect(screen.getByText('5 turns')).toBeInTheDocument();
        });

        it('renders singular turn for count of 1', () => {
            const sessions: SessionHistoryItem[] = [
                createMockSession({ turn_count: 1 }),
            ];

            render(<SessionHistoryList sessions={sessions} onSessionClick={mockOnSessionClick} />);

            expect(screen.getByText('1 turn')).toBeInTheDocument();
        });

        it('renders date in relative format', () => {
            const sessions: SessionHistoryItem[] = [
                createMockSession({ created_at: '2024-01-15T10:30:00Z' }),
            ];

            render(<SessionHistoryList sessions={sessions} onSessionClick={mockOnSessionClick} />);

            // Should show mocked relative time
            expect(screen.getByText('2 days ago')).toBeInTheDocument();
        });
    });

    describe('Attack Type Badge Colors', () => {
        const attackTypeTestCases: Array<{ attack_type: string; display: string; expectedColorClass: string }> = [
            { attack_type: 'nigerian_419', display: 'Nigerian 419', expectedColorClass: 'bg-orange-100' },
            { attack_type: 'ceo_fraud', display: 'CEO Fraud', expectedColorClass: 'bg-red-100' },
            { attack_type: 'fake_invoice', display: 'Fake Invoice', expectedColorClass: 'bg-yellow-100' },
            { attack_type: 'romance_scam', display: 'Romance Scam', expectedColorClass: 'bg-pink-100' },
            { attack_type: 'tech_support', display: 'Tech Support', expectedColorClass: 'bg-purple-100' },
            { attack_type: 'lottery_prize', display: 'Lottery Prize', expectedColorClass: 'bg-green-100' },
            { attack_type: 'crypto_investment', display: 'Crypto Investment', expectedColorClass: 'bg-blue-100' },
            { attack_type: 'delivery_scam', display: 'Delivery Scam', expectedColorClass: 'bg-teal-100' },
            { attack_type: 'not_phishing', display: 'Not Phishing', expectedColorClass: 'bg-gray-100' },
        ];

        it.each(attackTypeTestCases)(
            'renders $display badge with correct color class',
            ({ attack_type, display, expectedColorClass }) => {
                const sessions: SessionHistoryItem[] = [
                    createMockSession({ attack_type, attack_type_display: display }),
                ];

                render(<SessionHistoryList sessions={sessions} onSessionClick={mockOnSessionClick} />);

                const badge = screen.getByTestId('attack-type-badge');
                expect(badge).toHaveTextContent(display);
                expect(badge.className).toContain(expectedColorClass);
            }
        );

        it('falls back to not_phishing colors for unknown attack type', () => {
            const sessions: SessionHistoryItem[] = [
                createMockSession({ attack_type: 'unknown_type', attack_type_display: 'Unknown' }),
            ];

            render(<SessionHistoryList sessions={sessions} onSessionClick={mockOnSessionClick} />);

            const badge = screen.getByTestId('attack-type-badge');
            expect(badge.className).toContain('bg-gray-100');
        });

        it('falls back to not_phishing colors for null attack type', () => {
            const sessions: SessionHistoryItem[] = [
                createMockSession({ attack_type: null, attack_type_display: 'Unknown' }),
            ];

            render(<SessionHistoryList sessions={sessions} onSessionClick={mockOnSessionClick} />);

            const badge = screen.getByTestId('attack-type-badge');
            expect(badge.className).toContain('bg-gray-100');
        });
    });

    describe('Risk Score Indicators', () => {
        it('renders low risk score (1-3) with green color', () => {
            const lowRiskScores = [1, 2, 3];

            lowRiskScores.forEach((risk_score) => {
                const sessions: SessionHistoryItem[] = [
                    createMockSession({ session_id: `session-${risk_score}`, risk_score }),
                ];

                const { unmount } = render(
                    <SessionHistoryList sessions={sessions} onSessionClick={mockOnSessionClick} />
                );

                const riskElement = screen.getByTestId('risk-score');
                expect(riskElement.className).toContain('text-green-600');
                expect(riskElement).toHaveTextContent(`Low (${risk_score}/10)`);

                unmount();
            });
        });

        it('renders medium risk score (4-6) with yellow color', () => {
            const mediumRiskScores = [4, 5, 6];

            mediumRiskScores.forEach((risk_score) => {
                const sessions: SessionHistoryItem[] = [
                    createMockSession({ session_id: `session-${risk_score}`, risk_score }),
                ];

                const { unmount } = render(
                    <SessionHistoryList sessions={sessions} onSessionClick={mockOnSessionClick} />
                );

                const riskElement = screen.getByTestId('risk-score');
                expect(riskElement.className).toContain('text-yellow-600');
                expect(riskElement).toHaveTextContent(`Medium (${risk_score}/10)`);

                unmount();
            });
        });

        it('renders high risk score (7-10) with red color', () => {
            const highRiskScores = [7, 8, 9, 10];

            highRiskScores.forEach((risk_score) => {
                const sessions: SessionHistoryItem[] = [
                    createMockSession({ session_id: `session-${risk_score}`, risk_score }),
                ];

                const { unmount } = render(
                    <SessionHistoryList sessions={sessions} onSessionClick={mockOnSessionClick} />
                );

                const riskElement = screen.getByTestId('risk-score');
                expect(riskElement.className).toContain('text-red-600');
                expect(riskElement).toHaveTextContent(`High (${risk_score}/10)`);

                unmount();
            });
        });
    });

    describe('Click Handler', () => {
        it('calls onSessionClick with correct session_id when clicked', () => {
            const sessions: SessionHistoryItem[] = [
                createMockSession({ session_id: 'clickable-session-456' }),
            ];

            render(<SessionHistoryList sessions={sessions} onSessionClick={mockOnSessionClick} />);

            const sessionRow = screen.getByTestId('session-row-clickable-session-456');
            fireEvent.click(sessionRow);

            expect(mockOnSessionClick).toHaveBeenCalledTimes(1);
            expect(mockOnSessionClick).toHaveBeenCalledWith('clickable-session-456');
        });

        it('calls onSessionClick with correct session_id for each session', () => {
            const sessions: SessionHistoryItem[] = [
                createMockSession({ session_id: 'session-a' }),
                createMockSession({ session_id: 'session-b' }),
                createMockSession({ session_id: 'session-c' }),
            ];

            render(<SessionHistoryList sessions={sessions} onSessionClick={mockOnSessionClick} />);

            // Click second session
            fireEvent.click(screen.getByTestId('session-row-session-b'));

            expect(mockOnSessionClick).toHaveBeenCalledWith('session-b');
        });
    });

    describe('Date Formatting', () => {
        it('handles valid date strings', () => {
            const sessions: SessionHistoryItem[] = [
                createMockSession({ created_at: '2024-01-15T10:30:00Z' }),
            ];

            render(<SessionHistoryList sessions={sessions} onSessionClick={mockOnSessionClick} />);

            // Should render without error and show mocked value
            expect(screen.getByText('2 days ago')).toBeInTheDocument();
        });

        it('handles invalid date strings gracefully', async () => {
            // Reset mock to throw error for invalid dates
            const dateFns = await import('date-fns');
            vi.mocked(dateFns.formatDistanceToNow).mockImplementationOnce(() => {
                throw new Error('Invalid date');
            });

            const sessions: SessionHistoryItem[] = [
                createMockSession({ created_at: 'invalid-date' }),
            ];

            render(<SessionHistoryList sessions={sessions} onSessionClick={mockOnSessionClick} />);

            // Should show fallback text
            expect(screen.getByText('Unknown date')).toBeInTheDocument();
        });
    });

    describe('Empty Session List', () => {
        it('renders empty container when sessions array is empty', () => {
            render(<SessionHistoryList sessions={[]} onSessionClick={mockOnSessionClick} />);

            const list = screen.getByTestId('session-history-list');
            expect(list).toBeInTheDocument();
            expect(list.children.length).toBe(0);
        });
    });

    describe('Multiple Sessions', () => {
        it('renders all sessions in the list', () => {
            const sessions: SessionHistoryItem[] = [
                createMockSession({ session_id: 'session-1', attack_type_display: 'Nigerian 419' }),
                createMockSession({ session_id: 'session-2', attack_type_display: 'CEO Fraud', attack_type: 'ceo_fraud' }),
                createMockSession({ session_id: 'session-3', attack_type_display: 'Romance Scam', attack_type: 'romance_scam' }),
            ];

            render(<SessionHistoryList sessions={sessions} onSessionClick={mockOnSessionClick} />);

            expect(screen.getByText('Nigerian 419')).toBeInTheDocument();
            expect(screen.getByText('CEO Fraud')).toBeInTheDocument();
            expect(screen.getByText('Romance Scam')).toBeInTheDocument();
        });
    });
});
