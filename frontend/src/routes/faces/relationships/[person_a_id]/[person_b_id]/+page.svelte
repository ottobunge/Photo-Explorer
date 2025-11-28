<script lang="ts">
	import { onMount } from 'svelte';
	import { page } from '$app/stores';
	import { goto } from '$app/navigation';
	import { client, API_HOST } from '$lib/api/client';

	interface Photo {
		id: string;
		filename: string;
		thumbnail_url: string | null;
		taken_at: string | null;
	}

	interface Person {
		id: string;
		name: string | null;
		face_count: number;
		photo_count: number;
		representative_face_crop_url: string | null;
	}

	interface RelationshipPhotosResponse {
		person_a: Person;
		person_b: Person;
		shared_photos: Photo[];
		shared_photo_count: number;
	}

	let loading = $state(true);
	let error = $state<string | null>(null);
	let personA = $state<Person | null>(null);
	let personB = $state<Person | null>(null);
	let photos = $state<Photo[]>([]);
	let sharedPhotoCount = $state(0);

	// Get route parameters
	const personAId = $derived($page.params.person_a_id ?? '');
	const personBId = $derived($page.params.person_b_id ?? '');

	// Derived page title
	const pageTitle = $derived(
		personA && personB
			? `${getPersonDisplayName(personA)} & ${getPersonDisplayName(personB)} - Photos Together`
			: 'Photos Together - Photo Explorer'
	);

	onMount(() => {
		void loadRelationshipPhotos();
	});

	async function loadRelationshipPhotos(): Promise<void> {
		loading = true;
		error = null;
		try {
			const res = await client.get<RelationshipPhotosResponse>(
				`/faces/relationships/${personAId}/${personBId}/photos`
			);

			if (res.success && res.data) {
				personA = res.data.person_a;
				personB = res.data.person_b;
				photos = res.data.shared_photos;
				sharedPhotoCount = res.data.shared_photo_count;
			}
		} catch (err: unknown) {
			console.error('Failed to load relationship photos:', err);
			error = err instanceof Error ? err.message : 'Failed to load relationship photos';
		} finally {
			loading = false;
		}
	}

	function handleBackToGraph(): void {
		void goto('/faces?view=graph');
	}

	function getPersonDisplayName(person: Person | null): string {
		return person?.name ?? 'Unknown';
	}
</script>

<svelte:head>
	<title>{pageTitle}</title>
</svelte:head>

<div class="p-8">
	<!-- Header with back button -->
	<div class="mb-6">
		<button
			onclick={handleBackToGraph}
			class="inline-flex items-center gap-2 rounded-lg border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 transition-colors hover:bg-gray-50"
		>
			<svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
				<path
					stroke-linecap="round"
					stroke-linejoin="round"
					stroke-width="2"
					d="M10 19l-7-7m0 0l7-7m-7 7h18"
				/>
			</svg>
			Back to Graph
		</button>
	</div>

	{#if loading}
		<div class="py-12 text-center text-gray-500">Loading relationship photos...</div>
	{:else if error}
		<div class="rounded-lg bg-red-50 p-4 text-red-700">
			<p class="font-medium">Error loading relationship photos</p>
			<p class="mt-1 text-sm">{error}</p>
			<button
				onclick={() => loadRelationshipPhotos()}
				class="mt-4 rounded bg-red-600 px-4 py-2 text-white hover:bg-red-700"
			>
				Retry
			</button>
		</div>
	{:else if personA && personB}
		<!-- People Information -->
		<div class="mb-8">
			<h1 class="mb-6 text-3xl font-bold text-gray-900">Photos Together</h1>

			<div class="mb-6 flex flex-wrap items-center gap-8">
				<!-- Person A -->
				<div class="flex items-center gap-4">
					<div class="h-20 w-20 overflow-hidden rounded-full bg-gray-100">
						{#if personA.representative_face_crop_url}
							<img
								src="{API_HOST}{personA.representative_face_crop_url}"
								alt={getPersonDisplayName(personA)}
								class="h-full w-full object-cover"
							/>
						{:else}
							<div class="flex h-full items-center justify-center text-3xl text-gray-300">
								&#128100;
							</div>
						{/if}
					</div>
					<div>
						<p class="text-xl font-semibold text-gray-900">
							{getPersonDisplayName(personA)}
						</p>
						<p class="text-sm text-gray-500">
							{personA.photo_count}
							{personA.photo_count === 1 ? 'photo' : 'photos'}
						</p>
					</div>
				</div>

				<!-- Connector -->
				<div class="text-gray-400">
					<svg class="h-8 w-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path
							stroke-linecap="round"
							stroke-linejoin="round"
							stroke-width="2"
							d="M13 7l5 5m0 0l-5 5m5-5H6"
						/>
					</svg>
				</div>

				<!-- Person B -->
				<div class="flex items-center gap-4">
					<div class="h-20 w-20 overflow-hidden rounded-full bg-gray-100">
						{#if personB.representative_face_crop_url}
							<img
								src="{API_HOST}{personB.representative_face_crop_url}"
								alt={getPersonDisplayName(personB)}
								class="h-full w-full object-cover"
							/>
						{:else}
							<div class="flex h-full items-center justify-center text-3xl text-gray-300">
								&#128100;
							</div>
						{/if}
					</div>
					<div>
						<p class="text-xl font-semibold text-gray-900">
							{getPersonDisplayName(personB)}
						</p>
						<p class="text-sm text-gray-500">
							{personB.photo_count}
							{personB.photo_count === 1 ? 'photo' : 'photos'}
						</p>
					</div>
				</div>
			</div>

			<p class="text-gray-600">
				{sharedPhotoCount}
				{sharedPhotoCount === 1 ? 'photo' : 'photos'} together
			</p>
		</div>

		<!-- Photo Grid -->
		{#if photos.length === 0}
			<div class="rounded-lg bg-gray-50 p-12 text-center">
				<p class="text-gray-500">No photos found with both people together.</p>
			</div>
		{:else}
			<div class="grid grid-cols-2 gap-4 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6">
				{#each photos as photo (photo.id)}
					<a
						href="/photos/{photo.id}"
						class="photo-card group block cursor-pointer"
						data-testid="relationship-photo-card"
					>
						{#if photo.thumbnail_url}
							<img
								src="{API_HOST}{photo.thumbnail_url}"
								alt={photo.filename}
								class="aspect-square w-full rounded-lg object-cover"
								loading="lazy"
							/>
						{:else}
							<div
								class="flex aspect-square w-full items-center justify-center rounded-lg bg-gray-100"
							>
								<svg class="h-8 w-8 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
									<path
										stroke-linecap="round"
										stroke-linejoin="round"
										stroke-width="2"
										d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"
									/>
								</svg>
							</div>
						{/if}
						<p class="mt-1 truncate text-xs text-gray-500">{photo.filename}</p>
						{#if photo.taken_at}
							<p class="truncate text-xs text-gray-400">
								{new Date(photo.taken_at).toLocaleDateString()}
							</p>
						{/if}
					</a>
				{/each}
			</div>
		{/if}
	{/if}
</div>

<style>
	.photo-card {
		transition: transform 0.2s;
	}
	.photo-card:hover {
		transform: scale(1.02);
	}
</style>
