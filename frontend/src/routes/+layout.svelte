<script lang="ts">
	import '../app.css';
	import { page } from '$app/stores';

	const navItems = [
		{ href: '/', label: 'Home', icon: 'home' },
		{ href: '/upload', label: 'Upload', icon: 'upload' },
		{ href: '/search', label: 'Search', icon: 'search' },
		{ href: '/connectors', label: 'Connectors', icon: 'link' },
		{ href: '/albums', label: 'Albums', icon: 'folder' },
		{ href: '/faces', label: 'Faces', icon: 'users' },
		{ href: '/settings', label: 'Settings', icon: 'settings' }
	];

	function isActive(href: string, currentPath: string): boolean {
		if (href === '/') return currentPath === '/';
		return currentPath.startsWith(href);
	}
</script>

<div class="flex min-h-screen">
	<!-- Sidebar -->
	<nav class="w-64 border-r border-gray-200 bg-white">
		<div class="flex h-16 items-center border-b border-gray-200 px-6">
			<h1 class="text-xl font-bold text-primary-600">Photo Explorer</h1>
		</div>
		<ul class="space-y-1 p-4">
			{#each navItems as item}
				<li>
					<a
						href={item.href}
						class="flex items-center gap-3 rounded-lg px-4 py-2 text-gray-600 transition-colors hover:bg-gray-100 hover:text-gray-900"
						class:bg-primary-50={isActive(item.href, $page.url.pathname)}
						class:text-primary-700={isActive(item.href, $page.url.pathname)}
						class:font-medium={isActive(item.href, $page.url.pathname)}
					>
						<span class="text-lg">
							{#if item.icon === 'home'}📷{:else if item.icon === 'upload'}⬆️{:else if item.icon === 'search'}🔍{:else if item.icon === 'link'}🔗{:else if item.icon === 'folder'}📁{:else if item.icon === 'users'}👥{:else if item.icon === 'settings'}⚙️{/if}
						</span>
						{item.label}
					</a>
				</li>
			{/each}
		</ul>
	</nav>

	<!-- Main content -->
	<main class="flex-1 overflow-auto">
		<slot />
	</main>
</div>
