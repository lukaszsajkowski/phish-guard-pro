import { describe, it, expect } from 'vitest';
import {
    editReducer,
    initialEditState,
    EditState,
    EditAction,
} from '../ChatMessage';

describe('editReducer', () => {
    describe('initial state', () => {
        it('has viewing mode by default', () => {
            expect(initialEditState.mode).toBe('viewing');
        });

        it('has empty content by default', () => {
            expect(initialEditState.content).toBe('');
        });

        it('has no error by default', () => {
            expect(initialEditState.error).toBeNull();
        });
    });

    describe('START_EDIT action', () => {
        it('transitions from viewing to editing mode', () => {
            const state = initialEditState;
            const action: EditAction = { type: 'START_EDIT', initialContent: 'Hello' };

            const newState = editReducer(state, action);

            expect(newState.mode).toBe('editing');
        });

        it('sets content to initialContent', () => {
            const state = initialEditState;
            const action: EditAction = { type: 'START_EDIT', initialContent: 'Test content' };

            const newState = editReducer(state, action);

            expect(newState.content).toBe('Test content');
        });

        it('clears any existing error', () => {
            const state: EditState = {
                mode: 'viewing',
                content: '',
                error: 'Previous error',
            };
            const action: EditAction = { type: 'START_EDIT', initialContent: 'New content' };

            const newState = editReducer(state, action);

            expect(newState.error).toBeNull();
        });

        it('handles empty initial content', () => {
            const state = initialEditState;
            const action: EditAction = { type: 'START_EDIT', initialContent: '' };

            const newState = editReducer(state, action);

            expect(newState.mode).toBe('editing');
            expect(newState.content).toBe('');
        });
    });

    describe('UPDATE_CONTENT action', () => {
        it('updates content while in editing mode', () => {
            const state: EditState = {
                mode: 'editing',
                content: 'Old content',
                error: null,
            };
            const action: EditAction = { type: 'UPDATE_CONTENT', content: 'New content' };

            const newState = editReducer(state, action);

            expect(newState.content).toBe('New content');
        });

        it('preserves mode when updating content', () => {
            const state: EditState = {
                mode: 'editing',
                content: 'Old',
                error: null,
            };
            const action: EditAction = { type: 'UPDATE_CONTENT', content: 'New' };

            const newState = editReducer(state, action);

            expect(newState.mode).toBe('editing');
        });

        it('preserves error when updating content', () => {
            const state: EditState = {
                mode: 'editing',
                content: 'Old',
                error: 'Some error',
            };
            const action: EditAction = { type: 'UPDATE_CONTENT', content: 'New' };

            const newState = editReducer(state, action);

            expect(newState.error).toBe('Some error');
        });

        it('handles clearing content', () => {
            const state: EditState = {
                mode: 'editing',
                content: 'Some content',
                error: null,
            };
            const action: EditAction = { type: 'UPDATE_CONTENT', content: '' };

            const newState = editReducer(state, action);

            expect(newState.content).toBe('');
        });
    });

    describe('START_SAVE action', () => {
        it('transitions from editing to validating mode', () => {
            const state: EditState = {
                mode: 'editing',
                content: 'Content to save',
                error: null,
            };
            const action: EditAction = { type: 'START_SAVE' };

            const newState = editReducer(state, action);

            expect(newState.mode).toBe('validating');
        });

        it('preserves content during save', () => {
            const state: EditState = {
                mode: 'editing',
                content: 'My content',
                error: null,
            };
            const action: EditAction = { type: 'START_SAVE' };

            const newState = editReducer(state, action);

            expect(newState.content).toBe('My content');
        });

        it('clears error when starting save', () => {
            const state: EditState = {
                mode: 'editing',
                content: 'Content',
                error: 'Previous validation error',
            };
            const action: EditAction = { type: 'START_SAVE' };

            const newState = editReducer(state, action);

            expect(newState.error).toBeNull();
        });
    });

    describe('SAVE_SUCCESS action', () => {
        it('transitions from validating to viewing mode', () => {
            const state: EditState = {
                mode: 'validating',
                content: 'Saved content',
                error: null,
            };
            const action: EditAction = { type: 'SAVE_SUCCESS' };

            const newState = editReducer(state, action);

            expect(newState.mode).toBe('viewing');
        });

        it('clears content after successful save', () => {
            const state: EditState = {
                mode: 'validating',
                content: 'Content',
                error: null,
            };
            const action: EditAction = { type: 'SAVE_SUCCESS' };

            const newState = editReducer(state, action);

            expect(newState.content).toBe('');
        });

        it('clears error after successful save', () => {
            const state: EditState = {
                mode: 'validating',
                content: 'Content',
                error: 'Some error',
            };
            const action: EditAction = { type: 'SAVE_SUCCESS' };

            const newState = editReducer(state, action);

            expect(newState.error).toBeNull();
        });
    });

    describe('SAVE_ERROR action', () => {
        it('transitions from validating back to editing mode', () => {
            const state: EditState = {
                mode: 'validating',
                content: 'Content',
                error: null,
            };
            const action: EditAction = { type: 'SAVE_ERROR', error: 'Validation failed' };

            const newState = editReducer(state, action);

            expect(newState.mode).toBe('editing');
        });

        it('sets the error message', () => {
            const state: EditState = {
                mode: 'validating',
                content: 'Content',
                error: null,
            };
            const action: EditAction = { type: 'SAVE_ERROR', error: 'PII detected in response' };

            const newState = editReducer(state, action);

            expect(newState.error).toBe('PII detected in response');
        });

        it('preserves content on error', () => {
            const state: EditState = {
                mode: 'validating',
                content: 'User edited content',
                error: null,
            };
            const action: EditAction = { type: 'SAVE_ERROR', error: 'Error' };

            const newState = editReducer(state, action);

            expect(newState.content).toBe('User edited content');
        });
    });

    describe('CANCEL action', () => {
        it('transitions from editing to viewing mode', () => {
            const state: EditState = {
                mode: 'editing',
                content: 'Unsaved changes',
                error: null,
            };
            const action: EditAction = { type: 'CANCEL' };

            const newState = editReducer(state, action);

            expect(newState.mode).toBe('viewing');
        });

        it('clears content when canceling', () => {
            const state: EditState = {
                mode: 'editing',
                content: 'Unsaved content',
                error: null,
            };
            const action: EditAction = { type: 'CANCEL' };

            const newState = editReducer(state, action);

            expect(newState.content).toBe('');
        });

        it('clears error when canceling', () => {
            const state: EditState = {
                mode: 'editing',
                content: 'Content',
                error: 'Validation error',
            };
            const action: EditAction = { type: 'CANCEL' };

            const newState = editReducer(state, action);

            expect(newState.error).toBeNull();
        });

        it('can cancel from validating mode', () => {
            const state: EditState = {
                mode: 'validating',
                content: 'Content',
                error: null,
            };
            const action: EditAction = { type: 'CANCEL' };

            const newState = editReducer(state, action);

            expect(newState.mode).toBe('viewing');
            expect(newState.content).toBe('');
        });
    });

    describe('unknown action', () => {
        it('returns current state for unknown action type', () => {
            const state: EditState = {
                mode: 'editing',
                content: 'Content',
                error: null,
            };
            // @ts-expect-error - Testing unknown action type
            const action: EditAction = { type: 'UNKNOWN_ACTION' };

            const newState = editReducer(state, action);

            expect(newState).toEqual(state);
        });
    });

    describe('state machine flow', () => {
        it('handles complete edit-save-success flow', () => {
            // Start from viewing
            let state = initialEditState;
            expect(state.mode).toBe('viewing');

            // Start editing
            state = editReducer(state, { type: 'START_EDIT', initialContent: 'Original' });
            expect(state.mode).toBe('editing');
            expect(state.content).toBe('Original');

            // Update content
            state = editReducer(state, { type: 'UPDATE_CONTENT', content: 'Modified' });
            expect(state.content).toBe('Modified');

            // Start save
            state = editReducer(state, { type: 'START_SAVE' });
            expect(state.mode).toBe('validating');

            // Save succeeds
            state = editReducer(state, { type: 'SAVE_SUCCESS' });
            expect(state.mode).toBe('viewing');
            expect(state.content).toBe('');
            expect(state.error).toBeNull();
        });

        it('handles edit-save-error-retry-success flow', () => {
            let state = initialEditState;

            // Start editing
            state = editReducer(state, { type: 'START_EDIT', initialContent: 'Original' });
            state = editReducer(state, { type: 'UPDATE_CONTENT', content: 'Bad content' });

            // Try to save
            state = editReducer(state, { type: 'START_SAVE' });
            expect(state.mode).toBe('validating');

            // Save fails
            state = editReducer(state, { type: 'SAVE_ERROR', error: 'Invalid content' });
            expect(state.mode).toBe('editing');
            expect(state.error).toBe('Invalid content');
            expect(state.content).toBe('Bad content'); // Content preserved

            // Fix content
            state = editReducer(state, { type: 'UPDATE_CONTENT', content: 'Good content' });
            expect(state.content).toBe('Good content');

            // Try save again
            state = editReducer(state, { type: 'START_SAVE' });
            expect(state.error).toBeNull(); // Error cleared

            // Save succeeds
            state = editReducer(state, { type: 'SAVE_SUCCESS' });
            expect(state.mode).toBe('viewing');
        });

        it('handles edit-cancel flow', () => {
            let state = initialEditState;

            // Start editing
            state = editReducer(state, { type: 'START_EDIT', initialContent: 'Original' });
            state = editReducer(state, { type: 'UPDATE_CONTENT', content: 'Changed' });

            // Cancel
            state = editReducer(state, { type: 'CANCEL' });
            expect(state.mode).toBe('viewing');
            expect(state.content).toBe('');
        });
    });
});
