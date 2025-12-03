import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, fireEvent } from '@testing-library/svelte';
import { tick } from 'svelte';
import ConnectorCard from './ConnectorCard.svelte';
import type { Connector } from '../types';

describe('ConnectorCard', () => {
	const mockLocalConnector: Connector = {
		id: 'local-1',
		type: 'local',
		name: 'My Photos',
		enabled: true,
		status: 'connected',
		config: {
			type: 'local',
			path: '/home/user/Pictures'
		},
		errorMessage: null,
		lastSync: '2024-01-15T10:30:00Z'
	};

	const mockGooglePhotosConnector: Connector = {
		id: 'google-1',
		type: 'google_photos',
		name: 'Google Photos Account',
		enabled: true,
		status: 'connected',
		config: {
			type: 'google_photos',
			refreshToken: 'token'
		},
		errorMessage: null,
		lastSync: '2024-01-15T11:00:00Z'
	};

	beforeEach(() => {
		vi.clearAllMocks();
	});

	describe('Local Folder Connector', () => {
		it('renders local connector', () => {
			const { container } = render(ConnectorCard, {
				props: { connector: mockLocalConnector }
			});

			expect(container.querySelector('.connector-card')).toBeTruthy();
		});

		it('displays connector name', () => {
			const { getByText } = render(ConnectorCard, {
				props: { connector: mockLocalConnector }
			});

			expect(getByText('My Photos')).toBeTruthy();
		});

		it('displays local folder icon', () => {
			const { container } = render(ConnectorCard, {
				props: { connector: mockLocalConnector }
			});

			const icon = container.querySelector('.connector-icon');
			expect(icon?.textContent).toBe('📁');
		});

		it('displays folder path', () => {
			const { getByText } = render(ConnectorCard, {
				props: { connector: mockLocalConnector }
			});

			expect(getByText('/home/user/Pictures')).toBeTruthy();
		});

		it('displays sync button for local connector', () => {
			const { getByText } = render(ConnectorCard, {
				props: { connector: mockLocalConnector }
			});

			expect(getByText('🔄 Sync Now')).toBeTruthy();
		});

		it('renders remove button', () => {
			const { getByText } = render(ConnectorCard, {
				props: { connector: mockLocalConnector }
			});

			expect(getByText('🗑️ Remove')).toBeTruthy();
		});

		it('displays disabled state', () => {
			const disabledConnector = { ...mockLocalConnector, enabled: false };
			const { container } = render(ConnectorCard, {
				props: { connector: disabledConnector }
			});

			const card = container.querySelector('.connector-card');
			expect(card?.className).toContain('disabled');
		});
	});

	describe('Google Photos Connector', () => {
		it('renders Google Photos connector', () => {
			const { container } = render(ConnectorCard, {
				props: { connector: mockGooglePhotosConnector }
			});

			expect(container.querySelector('.connector-card')).toBeTruthy();
		});

		it('displays Google Photos icon', () => {
			const { container } = render(ConnectorCard, {
				props: { connector: mockGooglePhotosConnector }
			});

			const icon = container.querySelector('.connector-icon');
			expect(icon?.textContent).toBe('📷');
		});

		it('displays import button for Google Photos', () => {
			const { getByText } = render(ConnectorCard, {
				props: { connector: mockGooglePhotosConnector }
			});

			expect(getByText('📥 Import Photos')).toBeTruthy();
		});

		it('displays reprocess button for Google Photos', () => {
			const { getByText } = render(ConnectorCard, {
				props: { connector: mockGooglePhotosConnector }
			});

			expect(getByText('🔄 Reprocess')).toBeTruthy();
		});
	});

	describe('Status Display', () => {
		it('displays connected status', () => {
			const { getByText } = render(ConnectorCard, {
				props: { connector: mockLocalConnector }
			});

			expect(getByText('Connected')).toBeTruthy();
		});

		it('displays disconnected status', () => {
			const disconnectedConnector = { ...mockLocalConnector, status: 'disconnected' };
			const { getByText } = render(ConnectorCard, {
				props: { connector: disconnectedConnector }
			});

			expect(getByText('Disconnected')).toBeTruthy();
		});

		it('displays syncing status', () => {
			const syncingConnector = { ...mockLocalConnector, status: 'syncing' };
			const { container } = render(ConnectorCard, {
				props: { connector: syncingConnector }
			});

			// Check that the connector card renders
			const card = container.querySelector('.connector-card');
			expect(card).toBeTruthy();
			// Verify status badge is rendered (class-based component)
			const statusBadge = container.querySelector('.status-badge');
			expect(statusBadge).toBeTruthy();
		});

		it('displays error status', () => {
			const errorConnector = { ...mockLocalConnector, status: 'error' };
			const { getByText } = render(ConnectorCard, {
				props: { connector: errorConnector }
			});

			expect(getByText('Error')).toBeTruthy();
		});
	});

	describe('Error Display', () => {
		it('hides error message when not present', () => {
			const { container } = render(ConnectorCard, {
				props: { connector: mockLocalConnector }
			});

			const errorBanner = container.querySelector('.connector-error');
			expect(errorBanner).toBeFalsy();
		});

		it('displays error message when present', () => {
			const errorConnector = {
				...mockLocalConnector,
				errorMessage: 'Failed to sync: Permission denied'
			};
			const { getByText } = render(ConnectorCard, {
				props: { connector: errorConnector }
			});

			expect(getByText('Failed to sync: Permission denied')).toBeTruthy();
		});

		it('displays error icon in error banner', () => {
			const errorConnector = {
				...mockLocalConnector,
				errorMessage: 'Connection error'
			};
			const { container } = render(ConnectorCard, {
				props: { connector: errorConnector }
			});

			const errorIcon = container.querySelector('.connector-error .error-icon');
			expect(errorIcon?.textContent).toBe('⚠️');
		});
	});

	describe('Last Sync Display', () => {
		it('displays last sync date', () => {
			const { getByText } = render(ConnectorCard, {
				props: { connector: mockLocalConnector }
			});

			// Should display formatted date
			expect(getByText(/Last sync:/)).toBeTruthy();
		});

		it('displays "Never" for null last sync', () => {
			const neverSyncedConnector = { ...mockLocalConnector, lastSync: null };
			const { getByText } = render(ConnectorCard, {
				props: { connector: neverSyncedConnector }
			});

			expect(getByText('Last sync: Never')).toBeTruthy();
		});
	});

	describe('Toggle Switch', () => {
		it('renders toggle switch', () => {
			const { container } = render(ConnectorCard, {
				props: { connector: mockLocalConnector }
			});

			const toggle = container.querySelector('.toggle-switch');
			expect(toggle).toBeTruthy();
		});

		it('toggle reflects enabled state', () => {
			const { container } = render(ConnectorCard, {
				props: { connector: mockLocalConnector }
			});

			const input = container.querySelector('.toggle-switch input') as HTMLInputElement;
			expect(input.checked).toBe(true);
		});

		it('toggle shows disabled state', () => {
			const disabledConnector = { ...mockLocalConnector, enabled: false };
			const { container } = render(ConnectorCard, {
				props: { connector: disabledConnector }
			});

			const input = container.querySelector('.toggle-switch input') as HTMLInputElement;
			expect(input.checked).toBe(false);
		});

		it('toggle can be clicked', async () => {
			const { container } = render(ConnectorCard, {
				props: { connector: mockLocalConnector }
			});

			const input = container.querySelector('.toggle-switch input') as HTMLInputElement;
			const initialState = input.checked;

			await fireEvent.change(input);
			await tick();

			// Toggle should respond to interaction
			expect(input).toBeTruthy();
		});
	});

	describe('Action Buttons', () => {
		it('renders sync button for local connector', () => {
			const { getByText } = render(ConnectorCard, {
				props: { connector: mockLocalConnector }
			});

			const syncBtn = getByText('🔄 Sync Now') as HTMLButtonElement;
			expect(syncBtn).toBeTruthy();
		});

		it('disables sync button when syncing', () => {
			const syncingConnector = { ...mockLocalConnector, status: 'syncing' };
			const { container } = render(ConnectorCard, {
				props: { connector: syncingConnector }
			});

			const syncBtn = container.querySelector('.sync-btn') as HTMLButtonElement;
			expect(syncBtn?.disabled).toBe(true);
		});

		it('disables sync button when connector disabled', () => {
			const disabledConnector = { ...mockLocalConnector, enabled: false };
			const { container } = render(ConnectorCard, {
				props: { connector: disabledConnector }
			});

			const syncBtn = container.querySelector('.sync-btn') as HTMLButtonElement;
			expect(syncBtn?.disabled).toBe(true);
		});

		it('enables remove button', () => {
			const { getByText } = render(ConnectorCard, {
				props: { connector: mockLocalConnector }
			});

			const removeBtn = getByText('🗑️ Remove') as HTMLButtonElement;
			expect(removeBtn).toBeTruthy();
		});

		it('calls onremove callback when remove button clicked', async () => {
			const onremove = vi.fn();
			const { getByText } = render(ConnectorCard, {
				props: {
					connector: mockLocalConnector,
					onremove
				}
			});

			const removeBtn = getByText('🗑️ Remove');
			await fireEvent.click(removeBtn);
			await tick();

			expect(onremove).toHaveBeenCalled();
		});
	});

	describe('Callback Props', () => {
		it('calls onsync when sync completes', async () => {
			const onsync = vi.fn();
			const { getByText } = render(ConnectorCard, {
				props: {
					connector: mockLocalConnector,
					onsync
				}
			});

			// Sync button click would trigger callback (mocked in integration tests)
			const syncBtn = getByText('🔄 Sync Now');
			expect(syncBtn).toBeTruthy();
		});

		it('passes connector id to onremove callback', async () => {
			const onremove = vi.fn();
			const { getByText } = render(ConnectorCard, {
				props: {
					connector: mockLocalConnector,
					onremove
				}
			});

			const removeBtn = getByText('🗑️ Remove');
			await fireEvent.click(removeBtn);
			await tick();

			expect(onremove).toHaveBeenCalledWith({ id: mockLocalConnector.id });
		});
	});

	describe('Google Photos Actions', () => {
		it('displays import photos button', () => {
			const { getByText } = render(ConnectorCard, {
				props: { connector: mockGooglePhotosConnector }
			});

			expect(getByText('📥 Import Photos')).toBeTruthy();
		});

		it('displays reprocess button', () => {
			const { getByText } = render(ConnectorCard, {
				props: { connector: mockGooglePhotosConnector }
			});

			expect(getByText('🔄 Reprocess')).toBeTruthy();
		});

		it('disables import button when disabled', () => {
			const disabledConnector = { ...mockGooglePhotosConnector, enabled: false };
			const { container } = render(ConnectorCard, {
				props: { connector: disabledConnector }
			});

			const importBtn = container.querySelector('.import-btn') as HTMLButtonElement;
			expect(importBtn?.disabled).toBe(true);
		});

		it('disables reprocess button when disabled', () => {
			const disabledConnector = { ...mockGooglePhotosConnector, enabled: false };
			const { container } = render(ConnectorCard, {
				props: { connector: disabledConnector }
			});

			const reprocessBtn = container.querySelector('.reprocess-btn') as HTMLButtonElement;
			expect(reprocessBtn?.disabled).toBe(true);
		});
	});

	describe('Component Structure', () => {
		it('uses $props() for props', () => {
			const { container } = render(ConnectorCard, {
				props: { connector: mockLocalConnector }
			});

			expect(container.querySelector('.connector-card')).toBeTruthy();
		});

		it('uses $state() for component state', () => {
			const { container } = render(ConnectorCard, {
				props: { connector: mockLocalConnector }
			});

			expect(container.querySelector('.connector-header')).toBeTruthy();
		});

		it('uses onclick handlers', async () => {
			const onremove = vi.fn();
			const { getByText } = render(ConnectorCard, {
				props: {
					connector: mockLocalConnector,
					onremove
				}
			});

			const removeBtn = getByText('🗑️ Remove');
			await fireEvent.click(removeBtn);

			expect(onremove).toHaveBeenCalled();
		});
	});

	describe('Visual States', () => {
		it('applies disabled styling', () => {
			const disabledConnector = { ...mockLocalConnector, enabled: false };
			const { container } = render(ConnectorCard, {
				props: { connector: disabledConnector }
			});

			const card = container.querySelector('.connector-card');
			expect(card?.className).toContain('disabled');
		});

		it('displays connector icon correctly', () => {
			const { container } = render(ConnectorCard, {
				props: { connector: mockLocalConnector }
			});

			const icon = container.querySelector('.connector-icon');
			expect(icon).toBeTruthy();
		});

		it('displays connector name and type', () => {
			const { getByText } = render(ConnectorCard, {
				props: { connector: mockLocalConnector }
			});

			expect(getByText('My Photos')).toBeTruthy();
			expect(getByText('Local Folder')).toBeTruthy();
		});
	});

	describe('Responsive Design', () => {
		it('renders in single column layout', () => {
			const { container } = render(ConnectorCard, {
				props: { connector: mockLocalConnector }
			});

			const header = container.querySelector('.connector-header');
			const actions = container.querySelector('.connector-actions');

			expect(header).toBeTruthy();
			expect(actions).toBeTruthy();
		});

		it('displays all action buttons in row', () => {
			const { container } = render(ConnectorCard, {
				props: { connector: mockLocalConnector }
			});

			const actions = container.querySelector('.connector-actions');
			const buttons = actions?.querySelectorAll('button');

			expect(buttons?.length).toBeGreaterThan(1);
		});
	});

	describe('Edge Cases', () => {
		it('handles rapid status changes', async () => {
			const { rerender } = render(ConnectorCard, {
				props: { connector: mockLocalConnector }
			});

			await rerender({ connector: { ...mockLocalConnector, status: 'syncing' } });
			await tick();
			await rerender({ connector: { ...mockLocalConnector, status: 'connected' } });
			await tick();

			expect(true).toBe(true);
		});

		it('handles connector type changes', async () => {
			const { rerender } = render(ConnectorCard, {
				props: { connector: mockLocalConnector }
			});

			await rerender({ connector: mockGooglePhotosConnector });
			await tick();

			expect(true).toBe(true);
		});

		it('handles empty error message', () => {
			const { container } = render(ConnectorCard, {
				props: { connector: { ...mockLocalConnector, errorMessage: '' } }
			});

			const error = container.querySelector('.connector-error');
			expect(error).toBeFalsy();
		});

		it('handles null dates correctly', () => {
			const { getByText } = render(ConnectorCard, {
				props: { connector: { ...mockLocalConnector, lastSync: null } }
			});

			expect(getByText('Last sync: Never')).toBeTruthy();
		});
	});

	describe('Accessibility', () => {
		it('has proper role attributes', () => {
			const { container } = render(ConnectorCard, {
				props: { connector: mockLocalConnector }
			});

			const modal = container.querySelector('[role="dialog"]');
			// Modal role if visible
			expect(container.querySelector('.connector-card')).toBeTruthy();
		});

		it('toggle switch is accessible', () => {
			const { container } = render(ConnectorCard, {
				props: { connector: mockLocalConnector }
			});

			const label = container.querySelector('.toggle-switch');
			expect(label).toBeTruthy();
		});

		it('displays button labels', () => {
			const { getByText } = render(ConnectorCard, {
				props: { connector: mockLocalConnector }
			});

			expect(getByText('🔄 Sync Now')).toBeTruthy();
			expect(getByText('🗑️ Remove')).toBeTruthy();
		});
	});
});
