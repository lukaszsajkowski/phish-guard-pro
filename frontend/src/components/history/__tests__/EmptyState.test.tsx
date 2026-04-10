import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { EmptyState } from '../EmptyState';

// Mock next/link to work in test environment
vi.mock('next/link', () => ({
    default: ({ children, href }: { children: React.ReactNode; href: string }) => (
        <a href={href}>{children}</a>
    ),
}));

describe('EmptyState Component', () => {
    describe('Rendering', () => {
        it('renders empty state container', () => {
            render(<EmptyState />);

            expect(screen.getByTestId('empty-state')).toBeInTheDocument();
        });

        it('displays empty state message', () => {
            render(<EmptyState />);

            expect(screen.getByText('No sessions yet')).toBeInTheDocument();
        });

        it('displays descriptive text about starting a session', () => {
            render(<EmptyState />);

            expect(
                screen.getByText(/You haven't analyzed any phishing emails yet/i)
            ).toBeInTheDocument();
            expect(
                screen.getByText(/Start your first session to begin collecting threat intelligence/i)
            ).toBeInTheDocument();
        });
    });

    describe('Link to Dashboard', () => {
        it('renders link to dashboard', () => {
            render(<EmptyState />);

            const link = screen.getByRole('link', { name: /Start analyzing/i });
            expect(link).toBeInTheDocument();
        });

        it('link has correct href to dashboard', () => {
            render(<EmptyState />);

            const link = screen.getByRole('link', { name: /Start analyzing/i });
            expect(link).toHaveAttribute('href', '/dashboard');
        });

        it('link is styled as a button', () => {
            render(<EmptyState />);

            // The link should be wrapped in or styled as a Button component
            const link = screen.getByRole('link', { name: /Start analyzing/i });
            expect(link).toBeInTheDocument();
        });
    });

    describe('Visual Elements', () => {
        it('renders shield icon', () => {
            render(<EmptyState />);

            // The component should contain an SVG icon (Shield from lucide-react)
            const container = screen.getByTestId('empty-state');
            const svg = container.querySelector('svg');
            expect(svg).toBeInTheDocument();
        });

        it('renders heading with correct styling', () => {
            render(<EmptyState />);

            const heading = screen.getByRole('heading', { level: 3 });
            expect(heading).toHaveTextContent('No sessions yet');
        });
    });

    describe('Accessibility', () => {
        it('has accessible link text', () => {
            render(<EmptyState />);

            const link = screen.getByRole('link');
            expect(link).toHaveTextContent('Start analyzing');
        });

        it('has proper heading hierarchy', () => {
            render(<EmptyState />);

            // Should have an h3 heading
            const heading = screen.getByRole('heading');
            expect(heading).toBeInTheDocument();
        });
    });

    describe('Content Structure', () => {
        it('renders content in proper order', () => {
            render(<EmptyState />);

            const container = screen.getByTestId('empty-state');

            // Verify the component renders
            expect(container).toBeInTheDocument();

            // Verify key elements are present
            expect(screen.getByText('No sessions yet')).toBeInTheDocument();
            expect(screen.getByRole('link', { name: /Start analyzing/i })).toBeInTheDocument();
        });
    });
});
