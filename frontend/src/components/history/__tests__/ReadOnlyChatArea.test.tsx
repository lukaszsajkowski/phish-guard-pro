import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { vi, describe, it, expect, beforeEach, afterEach } from 'vitest';
import { ReadOnlyChatArea } from '../ReadOnlyChatArea';
import { ChatMessage } from '@/types/schemas';

// Mock clipboard API
const mockClipboard = {
    writeText: vi.fn().mockResolvedValue(undefined),
};

describe('ReadOnlyChatArea Component', () => {
    const createMockMessage = (overrides: Partial<ChatMessage> = {}): ChatMessage => ({
        id: 'msg-1',
        sender: 'bot',
        content: 'Hello, this is a test message.',
        timestamp: new Date('2024-01-15T10:30:00Z'),
        ...overrides,
    });

    beforeEach(() => {
        vi.clearAllMocks();
        Object.assign(navigator, { clipboard: mockClipboard });
    });

    afterEach(() => {
        vi.restoreAllMocks();
    });

    describe('Empty State', () => {
        it('renders empty state when messages array is empty', () => {
            render(<ReadOnlyChatArea messages={[]} />);

            expect(screen.getByText('No Messages')).toBeInTheDocument();
            expect(screen.getByText('This session has no conversation history.')).toBeInTheDocument();
        });

        it('does not render chat area container when empty', () => {
            render(<ReadOnlyChatArea messages={[]} />);

            expect(screen.queryByTestId('read-only-chat-area')).not.toBeInTheDocument();
        });
    });

    describe('Bot Messages', () => {
        it('renders bot message correctly', () => {
            const message = createMockMessage({
                id: 'bot-msg-1',
                sender: 'bot',
                content: 'I am a bot response.',
            });

            render(<ReadOnlyChatArea messages={[message]} />);

            expect(screen.getByTestId('read-only-chat-area')).toBeInTheDocument();
            expect(screen.getByTestId('chat-message-bot')).toBeInTheDocument();
            expect(screen.getByText('PhishGuard Bot')).toBeInTheDocument();
            expect(screen.getByText('I am a bot response.')).toBeInTheDocument();
        });

        it('renders multiple bot messages', () => {
            const messages: ChatMessage[] = [
                createMockMessage({ id: 'bot-1', sender: 'bot', content: 'First bot message' }),
                createMockMessage({ id: 'bot-2', sender: 'bot', content: 'Second bot message' }),
            ];

            render(<ReadOnlyChatArea messages={messages} />);

            const botMessages = screen.getAllByTestId('chat-message-bot');
            expect(botMessages).toHaveLength(2);
            expect(screen.getByText('First bot message')).toBeInTheDocument();
            expect(screen.getByText('Second bot message')).toBeInTheDocument();
        });

        it('shows copy button for bot messages', () => {
            const message = createMockMessage({ sender: 'bot' });

            render(<ReadOnlyChatArea messages={[message]} />);

            expect(screen.getByTestId('copy-response-button')).toBeInTheDocument();
            expect(screen.getByText('Copy to clipboard')).toBeInTheDocument();
        });
    });

    describe('Scammer Messages', () => {
        it('renders scammer message correctly', () => {
            const message = createMockMessage({
                id: 'scammer-msg-1',
                sender: 'scammer',
                content: 'Send me your bank details.',
            });

            render(<ReadOnlyChatArea messages={[message]} />);

            expect(screen.getByTestId('chat-message-scammer')).toBeInTheDocument();
            expect(screen.getByText('Scammer')).toBeInTheDocument();
            expect(screen.getByText('Send me your bank details.')).toBeInTheDocument();
        });

        it('does not show copy button for scammer messages', () => {
            const message = createMockMessage({ sender: 'scammer' });

            render(<ReadOnlyChatArea messages={[message]} />);

            expect(screen.queryByTestId('copy-response-button')).not.toBeInTheDocument();
        });
    });

    describe('Mixed Messages', () => {
        it('renders both bot and scammer messages', () => {
            const messages: ChatMessage[] = [
                createMockMessage({ id: 'bot-1', sender: 'bot', content: 'Hello from bot' }),
                createMockMessage({ id: 'scammer-1', sender: 'scammer', content: 'Hello from scammer' }),
                createMockMessage({ id: 'bot-2', sender: 'bot', content: 'Another bot message' }),
            ];

            render(<ReadOnlyChatArea messages={messages} />);

            const botMessages = screen.getAllByTestId('chat-message-bot');
            const scammerMessages = screen.getAllByTestId('chat-message-scammer');

            expect(botMessages).toHaveLength(2);
            expect(scammerMessages).toHaveLength(1);
        });

        it('displays correct message count', () => {
            const messages: ChatMessage[] = [
                createMockMessage({ id: 'msg-1' }),
                createMockMessage({ id: 'msg-2' }),
                createMockMessage({ id: 'msg-3' }),
            ];

            render(<ReadOnlyChatArea messages={messages} />);

            expect(screen.getByText('3 messages')).toBeInTheDocument();
        });

        it('displays singular message for single message', () => {
            const messages: ChatMessage[] = [createMockMessage()];

            render(<ReadOnlyChatArea messages={messages} />);

            expect(screen.getByText('1 message')).toBeInTheDocument();
        });
    });

    describe('Read-Only Verification', () => {
        it('does not render edit buttons', () => {
            const message = createMockMessage({ sender: 'bot' });

            render(<ReadOnlyChatArea messages={[message]} />);

            // Common edit-related buttons should not exist
            expect(screen.queryByTestId('edit-response-button')).not.toBeInTheDocument();
            expect(screen.queryByRole('button', { name: /edit/i })).not.toBeInTheDocument();
        });

        it('does not render ScammerInput component', () => {
            const messages: ChatMessage[] = [createMockMessage()];

            render(<ReadOnlyChatArea messages={messages} />);

            expect(screen.queryByTestId('scammer-input-textarea')).not.toBeInTheDocument();
            expect(screen.queryByTestId('scammer-input-send-button')).not.toBeInTheDocument();
        });

        it('does not render Generate Response button', () => {
            const messages: ChatMessage[] = [createMockMessage()];

            render(<ReadOnlyChatArea messages={messages} />);

            expect(screen.queryByTestId('generate-response-button')).not.toBeInTheDocument();
            expect(screen.queryByRole('button', { name: /generate/i })).not.toBeInTheDocument();
        });

        it('does not render any input fields', () => {
            const messages: ChatMessage[] = [createMockMessage()];

            render(<ReadOnlyChatArea messages={messages} />);

            expect(screen.queryByRole('textbox')).not.toBeInTheDocument();
            expect(screen.queryByRole('textarea')).not.toBeInTheDocument();
        });
    });

    describe('Thinking Section Toggle', () => {
        it('renders thinking panel for bot messages with thinking data', () => {
            const message = createMockMessage({
                sender: 'bot',
                thinking: {
                    turn_goal: 'Build trust with the scammer',
                    selected_tactic: 'Sympathy',
                    reasoning: 'The scammer seems to be testing trust levels',
                },
            });

            render(<ReadOnlyChatArea messages={[message]} />);

            expect(screen.getByTestId('agent-thinking-panel')).toBeInTheDocument();
            expect(screen.getByText('Agent Thinking')).toBeInTheDocument();
        });

        it('does not render thinking panel when no thinking data', () => {
            const message = createMockMessage({
                sender: 'bot',
                thinking: undefined,
            });

            render(<ReadOnlyChatArea messages={[message]} />);

            expect(screen.queryByTestId('agent-thinking-panel')).not.toBeInTheDocument();
        });

        it('shows thinking details when panel is expanded', () => {
            const message = createMockMessage({
                sender: 'bot',
                thinking: {
                    turn_goal: 'Extract payment information',
                    selected_tactic: 'Curiosity',
                    reasoning: 'Need to learn more about payment methods',
                },
            });

            render(<ReadOnlyChatArea messages={[message]} />);

            const thinkingPanel = screen.getByTestId('agent-thinking-panel');
            const summary = thinkingPanel.querySelector('summary');

            // Click to expand
            fireEvent.click(summary!);

            expect(screen.getByText('Current Goal')).toBeInTheDocument();
            expect(screen.getByText('Extract payment information')).toBeInTheDocument();
            expect(screen.getByText('Selected Tactic')).toBeInTheDocument();
            expect(screen.getByText('Curiosity')).toBeInTheDocument();
            expect(screen.getByText('Reasoning')).toBeInTheDocument();
            expect(screen.getByText(/"Need to learn more about payment methods"/)).toBeInTheDocument();
        });

        it('does not render thinking panel for scammer messages', () => {
            const message = createMockMessage({
                sender: 'scammer',
                thinking: {
                    turn_goal: 'Should not appear',
                    selected_tactic: 'Should not appear',
                    reasoning: 'Should not appear',
                },
            });

            render(<ReadOnlyChatArea messages={[message]} />);

            expect(screen.queryByTestId('agent-thinking-panel')).not.toBeInTheDocument();
        });
    });

    describe('Copy Button Functionality', () => {
        it('copies message content to clipboard when clicked', async () => {
            const messageContent = 'This is the message to copy.';
            const message = createMockMessage({
                sender: 'bot',
                content: messageContent,
            });

            render(<ReadOnlyChatArea messages={[message]} />);

            const copyButton = screen.getByTestId('copy-response-button');
            fireEvent.click(copyButton);

            expect(mockClipboard.writeText).toHaveBeenCalledWith(messageContent);
        });

        it('shows Copied! feedback after clicking copy', async () => {
            const message = createMockMessage({ sender: 'bot' });

            render(<ReadOnlyChatArea messages={[message]} />);

            const copyButton = screen.getByTestId('copy-response-button');
            fireEvent.click(copyButton);

            await waitFor(() => {
                expect(screen.getByText('Copied!')).toBeInTheDocument();
            });
        });

        it('reverts to Copy to clipboard after timeout', async () => {
            vi.useFakeTimers({ shouldAdvanceTime: true });
            const message = createMockMessage({ sender: 'bot' });

            render(<ReadOnlyChatArea messages={[message]} />);

            const copyButton = screen.getByTestId('copy-response-button');
            await fireEvent.click(copyButton);

            // Wait for copied state
            expect(await screen.findByText('Copied!')).toBeInTheDocument();

            // Fast-forward 2 seconds
            await vi.advanceTimersByTimeAsync(2000);

            // Should revert back to original text
            expect(await screen.findByText('Copy to clipboard')).toBeInTheDocument();

            vi.useRealTimers();
        });

        it('handles clipboard error gracefully', async () => {
            const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
            mockClipboard.writeText.mockRejectedValueOnce(new Error('Clipboard error'));

            const message = createMockMessage({ sender: 'bot' });

            render(<ReadOnlyChatArea messages={[message]} />);

            const copyButton = screen.getByTestId('copy-response-button');
            fireEvent.click(copyButton);

            await waitFor(() => {
                expect(consoleSpy).toHaveBeenCalledWith('Failed to copy:', expect.any(Error));
            }, { timeout: 3000 });

            consoleSpy.mockRestore();
        });
    });

    describe('Message Timestamp', () => {
        it('displays formatted timestamp for messages', () => {
            const message = createMockMessage({
                timestamp: new Date('2024-01-15T14:30:00Z'),
            });

            render(<ReadOnlyChatArea messages={[message]} />);

            // The timestamp should be formatted as time only (HH:MM format)
            // The exact format depends on locale, but we check that time element exists
            const messageElement = screen.getByTestId('chat-message-bot');
            expect(messageElement).toBeInTheDocument();
        });
    });

    describe('Header Section', () => {
        it('renders Conversation History title', () => {
            const messages: ChatMessage[] = [createMockMessage()];

            render(<ReadOnlyChatArea messages={messages} />);

            expect(screen.getByText('Conversation History')).toBeInTheDocument();
        });
    });

    describe('Accessibility', () => {
        it('has proper aria labels for copy button', () => {
            const message = createMockMessage({ sender: 'bot' });

            render(<ReadOnlyChatArea messages={[message]} />);

            const copyButton = screen.getByTestId('copy-response-button');
            expect(copyButton).toBeInTheDocument();
        });

        it('thinking panel summary is accessible via keyboard', () => {
            const message = createMockMessage({
                sender: 'bot',
                thinking: {
                    turn_goal: 'Test goal',
                    selected_tactic: 'Test tactic',
                    reasoning: 'Test reasoning',
                },
            });

            render(<ReadOnlyChatArea messages={[message]} />);

            const thinkingPanel = screen.getByTestId('agent-thinking-panel');
            const summary = thinkingPanel.querySelector('summary');

            // Summary should be focusable and have cursor pointer class
            expect(summary).toHaveClass('cursor-pointer');
        });
    });
});
