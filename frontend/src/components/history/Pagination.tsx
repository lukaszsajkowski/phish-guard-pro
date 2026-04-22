"use client";

import { ChevronLeft, ChevronRight, MoreHorizontal } from "lucide-react";
import { Button } from "@/components/ui/button";

interface PaginationProps {
    currentPage: number;
    totalPages: number;
    onPageChange: (page: number) => void;
}

export function Pagination({ currentPage, totalPages, onPageChange }: PaginationProps) {
    // Generate page numbers with ellipsis for large ranges
    const getPageNumbers = (): (number | "ellipsis")[] => {
        const pages: (number | "ellipsis")[] = [];
        const maxVisiblePages = 5;

        if (totalPages <= maxVisiblePages) {
            // Show all pages if total is small
            for (let i = 1; i <= totalPages; i++) {
                pages.push(i);
            }
        } else {
            // Always show first page
            pages.push(1);

            if (currentPage > 3) {
                pages.push("ellipsis");
            }

            // Show pages around current
            const start = Math.max(2, currentPage - 1);
            const end = Math.min(totalPages - 1, currentPage + 1);

            for (let i = start; i <= end; i++) {
                pages.push(i);
            }

            if (currentPage < totalPages - 2) {
                pages.push("ellipsis");
            }

            // Always show last page
            pages.push(totalPages);
        }

        return pages;
    };

    if (totalPages <= 1) {
        return null;
    }

    const pageNumbers = getPageNumbers();

    const handleKeyDown = (e: React.KeyboardEvent) => {
        if (e.key === "ArrowLeft" && currentPage > 1) {
            e.preventDefault();
            onPageChange(currentPage - 1);
        } else if (e.key === "ArrowRight" && currentPage < totalPages) {
            e.preventDefault();
            onPageChange(currentPage + 1);
        }
    };

    return (
        <nav
            className="flex items-center justify-center gap-1"
            aria-label="Pagination"
            data-testid="pagination"
            onKeyDown={handleKeyDown}
        >
            <Button
                variant="outline"
                size="icon-sm"
                onClick={() => onPageChange(currentPage - 1)}
                disabled={currentPage === 1}
                aria-label="Go to previous page"
                data-testid="pagination-prev"
            >
                <ChevronLeft className="h-4 w-4" />
            </Button>

            {pageNumbers.map((page, index) => {
                if (page === "ellipsis") {
                    return (
                        <span
                            key={`ellipsis-${index}`}
                            className="flex items-center justify-center w-8 h-8"
                            aria-hidden="true"
                        >
                            <MoreHorizontal className="h-4 w-4 text-muted-foreground" />
                        </span>
                    );
                }

                const isCurrentPage = page === currentPage;
                return (
                    <Button
                        key={page}
                        variant={isCurrentPage ? "default" : "outline"}
                        size="icon-sm"
                        onClick={() => onPageChange(page)}
                        aria-label={`Go to page ${page}`}
                        aria-current={isCurrentPage ? "page" : undefined}
                        data-testid={`pagination-page-${page}`}
                    >
                        {page}
                    </Button>
                );
            })}

            <Button
                variant="outline"
                size="icon-sm"
                onClick={() => onPageChange(currentPage + 1)}
                disabled={currentPage === totalPages}
                aria-label="Go to next page"
                data-testid="pagination-next"
            >
                <ChevronRight className="h-4 w-4" />
            </Button>
        </nav>
    );
}
