import { render, screen, fireEvent } from '@testing-library/react';
import { vi, describe, it, expect, beforeEach } from 'vitest';
import { Pagination } from '../Pagination';

describe('Pagination Component', () => {
    const mockOnPageChange = vi.fn();

    beforeEach(() => {
        mockOnPageChange.mockClear();
    });

    describe('Rendering', () => {
        it('renders pagination when totalPages is greater than 1', () => {
            render(
                <Pagination currentPage={1} totalPages={5} onPageChange={mockOnPageChange} />
            );

            expect(screen.getByTestId('pagination')).toBeInTheDocument();
        });

        it('does not render when totalPages is 1', () => {
            render(
                <Pagination currentPage={1} totalPages={1} onPageChange={mockOnPageChange} />
            );

            expect(screen.queryByTestId('pagination')).not.toBeInTheDocument();
        });

        it('does not render when totalPages is 0', () => {
            render(
                <Pagination currentPage={1} totalPages={0} onPageChange={mockOnPageChange} />
            );

            expect(screen.queryByTestId('pagination')).not.toBeInTheDocument();
        });
    });

    describe('Page Number Display', () => {
        it('displays all page numbers when totalPages is 5 or less', () => {
            render(
                <Pagination currentPage={1} totalPages={5} onPageChange={mockOnPageChange} />
            );

            expect(screen.getByTestId('pagination-page-1')).toBeInTheDocument();
            expect(screen.getByTestId('pagination-page-2')).toBeInTheDocument();
            expect(screen.getByTestId('pagination-page-3')).toBeInTheDocument();
            expect(screen.getByTestId('pagination-page-4')).toBeInTheDocument();
            expect(screen.getByTestId('pagination-page-5')).toBeInTheDocument();
        });

        it('displays correct page numbers for 3 pages', () => {
            render(
                <Pagination currentPage={2} totalPages={3} onPageChange={mockOnPageChange} />
            );

            expect(screen.getByTestId('pagination-page-1')).toBeInTheDocument();
            expect(screen.getByTestId('pagination-page-2')).toBeInTheDocument();
            expect(screen.getByTestId('pagination-page-3')).toBeInTheDocument();
        });

        it('highlights current page', () => {
            render(
                <Pagination currentPage={3} totalPages={5} onPageChange={mockOnPageChange} />
            );

            const currentPageButton = screen.getByTestId('pagination-page-3');
            expect(currentPageButton).toHaveAttribute('aria-current', 'page');
        });

        it('non-current pages do not have aria-current', () => {
            render(
                <Pagination currentPage={3} totalPages={5} onPageChange={mockOnPageChange} />
            );

            const otherPageButton = screen.getByTestId('pagination-page-1');
            expect(otherPageButton).not.toHaveAttribute('aria-current');
        });
    });

    describe('Previous Button', () => {
        it('is disabled on first page', () => {
            render(
                <Pagination currentPage={1} totalPages={5} onPageChange={mockOnPageChange} />
            );

            const prevButton = screen.getByTestId('pagination-prev');
            expect(prevButton).toBeDisabled();
        });

        it('is enabled on page 2', () => {
            render(
                <Pagination currentPage={2} totalPages={5} onPageChange={mockOnPageChange} />
            );

            const prevButton = screen.getByTestId('pagination-prev');
            expect(prevButton).not.toBeDisabled();
        });

        it('is enabled on last page', () => {
            render(
                <Pagination currentPage={5} totalPages={5} onPageChange={mockOnPageChange} />
            );

            const prevButton = screen.getByTestId('pagination-prev');
            expect(prevButton).not.toBeDisabled();
        });

        it('calls onPageChange with previous page number when clicked', () => {
            render(
                <Pagination currentPage={3} totalPages={5} onPageChange={mockOnPageChange} />
            );

            const prevButton = screen.getByTestId('pagination-prev');
            fireEvent.click(prevButton);

            expect(mockOnPageChange).toHaveBeenCalledTimes(1);
            expect(mockOnPageChange).toHaveBeenCalledWith(2);
        });

        it('has correct aria-label', () => {
            render(
                <Pagination currentPage={3} totalPages={5} onPageChange={mockOnPageChange} />
            );

            const prevButton = screen.getByTestId('pagination-prev');
            expect(prevButton).toHaveAttribute('aria-label', 'Go to previous page');
        });
    });

    describe('Next Button', () => {
        it('is disabled on last page', () => {
            render(
                <Pagination currentPage={5} totalPages={5} onPageChange={mockOnPageChange} />
            );

            const nextButton = screen.getByTestId('pagination-next');
            expect(nextButton).toBeDisabled();
        });

        it('is enabled on first page when there are multiple pages', () => {
            render(
                <Pagination currentPage={1} totalPages={5} onPageChange={mockOnPageChange} />
            );

            const nextButton = screen.getByTestId('pagination-next');
            expect(nextButton).not.toBeDisabled();
        });

        it('is enabled on page 4 of 5', () => {
            render(
                <Pagination currentPage={4} totalPages={5} onPageChange={mockOnPageChange} />
            );

            const nextButton = screen.getByTestId('pagination-next');
            expect(nextButton).not.toBeDisabled();
        });

        it('calls onPageChange with next page number when clicked', () => {
            render(
                <Pagination currentPage={3} totalPages={5} onPageChange={mockOnPageChange} />
            );

            const nextButton = screen.getByTestId('pagination-next');
            fireEvent.click(nextButton);

            expect(mockOnPageChange).toHaveBeenCalledTimes(1);
            expect(mockOnPageChange).toHaveBeenCalledWith(4);
        });

        it('has correct aria-label', () => {
            render(
                <Pagination currentPage={3} totalPages={5} onPageChange={mockOnPageChange} />
            );

            const nextButton = screen.getByTestId('pagination-next');
            expect(nextButton).toHaveAttribute('aria-label', 'Go to next page');
        });
    });

    describe('Page Number Click Handler', () => {
        it('calls onPageChange with correct page number when page is clicked', () => {
            render(
                <Pagination currentPage={1} totalPages={5} onPageChange={mockOnPageChange} />
            );

            const page3Button = screen.getByTestId('pagination-page-3');
            fireEvent.click(page3Button);

            expect(mockOnPageChange).toHaveBeenCalledTimes(1);
            expect(mockOnPageChange).toHaveBeenCalledWith(3);
        });

        it('calls onPageChange when clicking on current page', () => {
            render(
                <Pagination currentPage={2} totalPages={5} onPageChange={mockOnPageChange} />
            );

            const currentPageButton = screen.getByTestId('pagination-page-2');
            fireEvent.click(currentPageButton);

            expect(mockOnPageChange).toHaveBeenCalledWith(2);
        });

        it('page buttons have correct aria-labels', () => {
            render(
                <Pagination currentPage={1} totalPages={3} onPageChange={mockOnPageChange} />
            );

            expect(screen.getByTestId('pagination-page-1')).toHaveAttribute('aria-label', 'Go to page 1');
            expect(screen.getByTestId('pagination-page-2')).toHaveAttribute('aria-label', 'Go to page 2');
            expect(screen.getByTestId('pagination-page-3')).toHaveAttribute('aria-label', 'Go to page 3');
        });
    });

    describe('Ellipsis Display', () => {
        it('shows ellipsis when there are many pages and current page is in the middle', () => {
            render(
                <Pagination currentPage={5} totalPages={10} onPageChange={mockOnPageChange} />
            );

            // Should show: 1 ... 4 5 6 ... 10
            expect(screen.getByTestId('pagination-page-1')).toBeInTheDocument();
            expect(screen.getByTestId('pagination-page-4')).toBeInTheDocument();
            expect(screen.getByTestId('pagination-page-5')).toBeInTheDocument();
            expect(screen.getByTestId('pagination-page-6')).toBeInTheDocument();
            expect(screen.getByTestId('pagination-page-10')).toBeInTheDocument();

            // Check for ellipsis (MoreHorizontal icons)
            const ellipsisElements = document.querySelectorAll('[aria-hidden="true"]');
            expect(ellipsisElements.length).toBeGreaterThanOrEqual(2);
        });

        it('shows ellipsis only after first page when on page 2', () => {
            render(
                <Pagination currentPage={2} totalPages={10} onPageChange={mockOnPageChange} />
            );

            // Should show: 1 2 3 ... 10
            expect(screen.getByTestId('pagination-page-1')).toBeInTheDocument();
            expect(screen.getByTestId('pagination-page-2')).toBeInTheDocument();
            expect(screen.getByTestId('pagination-page-3')).toBeInTheDocument();
            expect(screen.getByTestId('pagination-page-10')).toBeInTheDocument();
        });

        it('shows ellipsis only before last page when near end', () => {
            render(
                <Pagination currentPage={9} totalPages={10} onPageChange={mockOnPageChange} />
            );

            // Should show: 1 ... 8 9 10
            expect(screen.getByTestId('pagination-page-1')).toBeInTheDocument();
            expect(screen.getByTestId('pagination-page-8')).toBeInTheDocument();
            expect(screen.getByTestId('pagination-page-9')).toBeInTheDocument();
            expect(screen.getByTestId('pagination-page-10')).toBeInTheDocument();
        });

        it('does not show ellipsis when totalPages is 5 or less', () => {
            render(
                <Pagination currentPage={3} totalPages={5} onPageChange={mockOnPageChange} />
            );

            // All pages should be visible, no ellipsis
            expect(screen.getByTestId('pagination-page-1')).toBeInTheDocument();
            expect(screen.getByTestId('pagination-page-2')).toBeInTheDocument();
            expect(screen.getByTestId('pagination-page-3')).toBeInTheDocument();
            expect(screen.getByTestId('pagination-page-4')).toBeInTheDocument();
            expect(screen.getByTestId('pagination-page-5')).toBeInTheDocument();

            // No ellipsis containers should be present (span elements with aria-hidden)
            // Note: icons inside buttons also have aria-hidden, so we look for span containers with the specific class
            const pagination = screen.getByTestId('pagination');
            const ellipsisSpans = pagination.querySelectorAll('span[aria-hidden="true"]');
            expect(ellipsisSpans.length).toBe(0);
        });
    });

    describe('Edge Cases', () => {
        it('handles page 1 of 2', () => {
            render(
                <Pagination currentPage={1} totalPages={2} onPageChange={mockOnPageChange} />
            );

            expect(screen.getByTestId('pagination-page-1')).toBeInTheDocument();
            expect(screen.getByTestId('pagination-page-2')).toBeInTheDocument();
            expect(screen.getByTestId('pagination-prev')).toBeDisabled();
            expect(screen.getByTestId('pagination-next')).not.toBeDisabled();
        });

        it('handles page 2 of 2', () => {
            render(
                <Pagination currentPage={2} totalPages={2} onPageChange={mockOnPageChange} />
            );

            expect(screen.getByTestId('pagination-page-1')).toBeInTheDocument();
            expect(screen.getByTestId('pagination-page-2')).toBeInTheDocument();
            expect(screen.getByTestId('pagination-prev')).not.toBeDisabled();
            expect(screen.getByTestId('pagination-next')).toBeDisabled();
        });

        it('handles large page count (100 pages)', () => {
            render(
                <Pagination currentPage={50} totalPages={100} onPageChange={mockOnPageChange} />
            );

            // Should show first, last, and pages around current
            expect(screen.getByTestId('pagination-page-1')).toBeInTheDocument();
            expect(screen.getByTestId('pagination-page-49')).toBeInTheDocument();
            expect(screen.getByTestId('pagination-page-50')).toBeInTheDocument();
            expect(screen.getByTestId('pagination-page-51')).toBeInTheDocument();
            expect(screen.getByTestId('pagination-page-100')).toBeInTheDocument();
        });

        it('handles first page with many pages', () => {
            render(
                <Pagination currentPage={1} totalPages={100} onPageChange={mockOnPageChange} />
            );

            expect(screen.getByTestId('pagination-page-1')).toBeInTheDocument();
            expect(screen.getByTestId('pagination-page-2')).toBeInTheDocument();
            expect(screen.getByTestId('pagination-page-100')).toBeInTheDocument();
            expect(screen.getByTestId('pagination-prev')).toBeDisabled();
        });

        it('handles last page with many pages', () => {
            render(
                <Pagination currentPage={100} totalPages={100} onPageChange={mockOnPageChange} />
            );

            expect(screen.getByTestId('pagination-page-1')).toBeInTheDocument();
            expect(screen.getByTestId('pagination-page-99')).toBeInTheDocument();
            expect(screen.getByTestId('pagination-page-100')).toBeInTheDocument();
            expect(screen.getByTestId('pagination-next')).toBeDisabled();
        });
    });

    describe('Accessibility', () => {
        it('has navigation role with aria-label', () => {
            render(
                <Pagination currentPage={1} totalPages={5} onPageChange={mockOnPageChange} />
            );

            const nav = screen.getByTestId('pagination');
            expect(nav).toHaveAttribute('aria-label', 'Pagination');
        });

        it('ellipsis elements are hidden from screen readers', () => {
            render(
                <Pagination currentPage={5} totalPages={10} onPageChange={mockOnPageChange} />
            );

            const ellipsisElements = document.querySelectorAll('[aria-hidden="true"]');
            ellipsisElements.forEach((element) => {
                expect(element).toHaveAttribute('aria-hidden', 'true');
            });
        });
    });
});
