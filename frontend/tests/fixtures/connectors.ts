/**
 * Test fixtures for connector mock data
 *
 * These fixtures provide reusable, realistic mock data for connectors
 * to be used across unit and E2E tests.
 */

export interface MockConnector {
	id: string;
	type: 'local' | 'google_photos' | 'upload';
	name: string;
	enabled: boolean;
	config?: Record<string, any>;
	created_at?: string;
	updated_at?: string;
}

/**
 * Create a mock connector with default values that can be overridden
 *
 * @example
 * const connector = createMockConnector({ type: 'local', name: 'My Photos' });
 */
export function createMockConnector(overrides: Partial<MockConnector> = {}): MockConnector {
	const id = overrides.id ?? `connector-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
	const type = overrides.type ?? 'local';

	// Type-specific defaults
	const typeDefaults: Record<string, Partial<MockConnector>> = {
		local: {
			name: 'Local Folder',
			config: { path: '/home/user/photos', recursive: true }
		},
		google_photos: {
			name: 'Google Photos',
			config: { account_email: 'user@gmail.com' }
		},
		upload: {
			name: 'Uploads',
			config: {}
		}
	};

	return {
		id,
		type,
		name: overrides.name ?? typeDefaults[type]?.name ?? 'Connector',
		enabled: overrides.enabled ?? true,
		config: overrides.config ?? typeDefaults[type]?.config ?? {},
		created_at: overrides.created_at ?? new Date().toISOString(),
		updated_at: overrides.updated_at ?? new Date().toISOString()
	};
}

/**
 * Create multiple mock connectors at once
 *
 * @example
 * const connectors = createMockConnectors(2, (index) => ({
 *   name: `Connector ${index + 1}`
 * }));
 */
export function createMockConnectors(
	count: number,
	overridesFn?: (index: number) => Partial<MockConnector>
): MockConnector[] {
	return Array.from({ length: count }, (_, index) =>
		createMockConnector(overridesFn ? overridesFn(index) : {})
	);
}

// Common test scenarios

/**
 * Local folder connector
 */
export const localConnector = createMockConnector({
	id: 'local-connector-id',
	type: 'local',
	name: 'My Photos',
	config: {
		path: '/home/user/photos',
		recursive: true,
		watch: false
	}
});

/**
 * Google Photos connector
 */
export const googlePhotosConnector = createMockConnector({
	id: 'google-connector-id',
	type: 'google_photos',
	name: 'Google Photos',
	config: {
		account_email: 'user@gmail.com',
		sync_enabled: true
	}
});

/**
 * Upload connector (default)
 */
export const uploadConnector = createMockConnector({
	id: 'upload-connector-id',
	type: 'upload',
	name: 'Uploads'
});

/**
 * Disabled connector
 */
export const disabledConnector = createMockConnector({
	id: 'disabled-connector-id',
	type: 'local',
	name: 'Disabled Folder',
	enabled: false
});

/**
 * Collection of diverse connectors
 */
export const diverseConnectors = [
	localConnector,
	googlePhotosConnector,
	uploadConnector
];

/**
 * Multiple local connectors
 */
export const multipleLocalConnectors = [
	createMockConnector({
		id: 'local-1',
		type: 'local',
		name: 'Family Photos',
		config: { path: '/home/user/family', recursive: true }
	}),
	createMockConnector({
		id: 'local-2',
		type: 'local',
		name: 'Vacation Photos',
		config: { path: '/home/user/vacation', recursive: true }
	}),
	createMockConnector({
		id: 'local-3',
		type: 'local',
		name: 'Work Photos',
		config: { path: '/home/user/work', recursive: false }
	})
];
