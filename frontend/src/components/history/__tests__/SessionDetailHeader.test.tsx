import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { vi, describe, it, expect, beforeEach } from 'vitest';
import { SessionDetailHeader } from '../SessionDetailHeader';

// Mock date-fns format function for consistent test results
vi.mock('date-fns', () => ({
    format: vi.fn(() => {
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

    describe('Status Badge', () => {
        it('renders active status with dot indicator', () => {
            render(<SessionDetailHeader {...defaultProps} status="active" />);

            const badge = screen.getByTestId('status-badge');
            expect(badge).toHaveTextContent('Active');
        });

        it('renders completed status', () => {
            render(<SessionDetailHeader {...defaultProps} status="completed" />);

            const badge = screen.getByTestId('status-badge');
            expect(badge).toHaveTextContent('Completed');
        });

        it('renders archived status', () => {
            render(<SessionDetailHeader {...defaultProps} status="archived" />);

            const badge = screen.getByTestId('status-badge');
            expect(badge).toHaveTextContent('Archived');
        });
    });

    describe('Date Formatting', () => {
        it('formats valid date string correctly', () => {
            render(<SessionDetailHeader {...defaultProps} createdAt="2024-01-15T10:30:00Z" />);

            expect(screen.getByTestId('created-at')).toHaveTextContent('Jan 15, 2024, 10:30 AM');
        });

        it('shows Unknown date for invalid date string', async () => {
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

            expect(screen.getByTestId('status-badge')).toHaveTextContent('COMPLETED');
        });
    });

    describe('Action Buttons', () => {
        it('renders export session button', () => {
            render(<SessionDetailHeader {...defaultProps} />);

            expect(screen.getByTestId('export-session-button')).toBeInTheDocument();
            expect(screen.getByTestId('export-session-button')).toHaveTextContent('Export Session');
        });

        it('renders export data dropdown button', () => {
            render(<SessionDetailHeader {...defaultProps} />);

            expect(screen.getByTestId('export-data-button')).toBeInTheDocument();
            expect(screen.getByTestId('export-data-button')).toHaveTextContent('Export Data');
        });

        it('opens dropdown and shows JSON/CSV options when export data clicked', async () => {
            const user = userEvent.setup();
            render(<SessionDetailHeader {...defaultProps} />);

            await user.click(screen.getByTestId('export-data-button'));

            await waitFor(() => {
                expect(screen.getByTestId('export-json-button')).toBeInTheDocument();
                expect(screen.getByTestId('export-csv-button')).toBeInTheDocument();
            });
        });

        it('calls onExportJson when JSON option clicked', async () => {
            const user = userEvent.setup();
            const onExportJson = vi.fn();
            render(<SessionDetailHeader {...defaultProps} onExportJson={onExportJson} />);

            await user.click(screen.getByTestId('export-data-button'));
            await waitFor(() => {
                expect(screen.getByTestId('export-json-button')).toBeInTheDocument();
            });
            await user.click(screen.getByTestId('export-json-button'));

            expect(onExportJson).toHaveBeenCalledTimes(1);
        });

        it('calls onExportCsv when CSV option clicked', async () => {
            const user = userEvent.setup();
            const onExportCsv = vi.fn();
            render(<SessionDetailHeader {...defaultProps} onExportCsv={onExportCsv} />);

            await user.click(screen.getByTestId('export-data-button'));
            await waitFor(() => {
                expect(screen.getByTestId('export-csv-button')).toBeInTheDocument();
            });
            await user.click(screen.getByTestId('export-csv-button'));

            expect(onExportCsv).toHaveBeenCalledTimes(1);
        });

    });
});
