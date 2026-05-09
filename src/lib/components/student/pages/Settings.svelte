<!-- Settings.svelte -->
<script lang="ts">
	import { getContext } from 'svelte';
	import { updateUserProfile, updateUserPassword, getSessionUser } from '$lib/apis/auths';
	import { onMount } from 'svelte';

	const i18n = getContext('i18n');
	
	let token: string = '';
	let loading = false;
	let successMessage = '';
	let errorMessage = '';
	let activeTab: 'profile' | 'password' = 'profile';

	// Profile form state
	let profileName = '';
	let profileImageUrl = '';
	let profileSaving = false;
	let profileError = '';
	let profileSuccess = '';

	// Password form state
	let currentPassword = '';
	let newPassword = '';
	let confirmPassword = '';
	let passwordSaving = false;
	let passwordError = '';
	let passwordSuccess = '';

	onMount(async () => {
		// Get token from localStorage
		const storedToken = localStorage.getItem('token');
		if (storedToken) {
			token = storedToken;
			await loadUserData();
		}
	});

	async function loadUserData() {
		try {
			loading = true;
			const user = await getSessionUser(token);
			if (user) {
				profileName = user.name || '';
				profileImageUrl = user.profile_image_url || '';
			}
		} catch (error) {
			console.error('Error loading user data:', error);
		} finally {
			loading = false;
		}
	}

	async function handleProfileUpdate() {
		profileError = '';
		profileSuccess = '';

		if (!profileName.trim()) {
			profileError = $i18n.t('Name is required');
			return;
		}

		try {
			profileSaving = true;
			await updateUserProfile(token, profileName, profileImageUrl);
			profileSuccess = $i18n.t('Profile updated successfully');
			setTimeout(() => {
				profileSuccess = '';
			}, 3000);
		} catch (error: any) {
			profileError = error?.message || $i18n.t('Error updating profile');
		} finally {
			profileSaving = false;
		}
	}

	async function handlePasswordChange() {
		passwordError = '';
		passwordSuccess = '';

		// Validation
		if (!currentPassword.trim()) {
			passwordError = $i18n.t('Current Password') + ' ' + $i18n.t('is required');
			return;
		}

		if (!newPassword.trim()) {
			passwordError = $i18n.t('New password is required');
			return;
		}

		if (newPassword.length < 8) {
			passwordError = $i18n.t('Password must be at least 8 characters long');
			return;
		}

		if (newPassword !== confirmPassword) {
			passwordError = $i18n.t('Passwords do not match');
			return;
		}

		try {
			passwordSaving = true;
			await updateUserPassword(token, currentPassword, newPassword);
			passwordSuccess = $i18n.t('Password changed successfully');
			// Reset form
			currentPassword = '';
			newPassword = '';
			confirmPassword = '';
			setTimeout(() => {
				passwordSuccess = '';
			}, 3000);
		} catch (error: any) {
			passwordError = error?.message || $i18n.t('Error changing password');
		} finally {
			passwordSaving = false;
		}
	}
</script>

<div class="mb-6">
	<h2 class="text-2xl font-bold text-gray-800 dark:text-gray-100 mb-4">{$i18n.t('Account Settings')}</h2>
</div>

{#if loading}
	<div class="flex justify-center items-center py-8">
		<div class="text-gray-600 dark:text-gray-400">Loading...</div>
	</div>
{:else}
	<div class="bg-white dark:bg-gray-800 rounded-lg shadow-md overflow-hidden">
		<!-- Tabs -->
		<div class="flex border-b border-gray-200 dark:border-gray-700">
			<button
				on:click={() => (activeTab = 'profile')}
				class={`flex-1 px-4 py-3 text-sm font-medium transition-colors ${
					activeTab === 'profile'
						? 'border-b-2 border-blue-500 text-blue-600 dark:text-blue-400'
						: 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-200'
				}`}
			>
				{$i18n.t('Profile')}
			</button>
			<button
				on:click={() => (activeTab = 'password')}
				class={`flex-1 px-4 py-3 text-sm font-medium transition-colors ${
					activeTab === 'password'
						? 'border-b-2 border-blue-500 text-blue-600 dark:text-blue-400'
						: 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-200'
				}`}
			>
				{$i18n.t('Change Password')}
			</button>
		</div>

		<!-- Profile Tab -->
		{#if activeTab === 'profile'}
			<div class="p-6">
				<form on:submit|preventDefault={handleProfileUpdate} class="space-y-4">
					<!-- Full Name Input -->
					<div>
						<label for="name" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
							{$i18n.t('Name')}
						</label>
						<input
							id="name"
							type="text"
							bind:value={profileName}
							placeholder={$i18n.t('Enter your full name')}
							class="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white placeholder-gray-400 dark:placeholder-gray-500 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
						/>
					</div>

					<!-- Profile Image URL (Optional) -->
					<div>
						<label for="profileImage" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
							{$i18n.t('Profile Image URL')} ({$i18n.t('Optional')})
						</label>
						<input
							id="profileImage"
							type="url"
							bind:value={profileImageUrl}
							placeholder="https://example.com/avatar.jpg"
							class="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white placeholder-gray-400 dark:placeholder-gray-500 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
						/>
					</div>

					<!-- Error Message -->
					{#if profileError}
						<div class="p-3 bg-red-100 dark:bg-red-900 text-red-700 dark:text-red-200 rounded-lg text-sm">
							{profileError}
						</div>
					{/if}

					<!-- Success Message -->
					{#if profileSuccess}
						<div class="p-3 bg-green-100 dark:bg-green-900 text-green-700 dark:text-green-200 rounded-lg text-sm">
							{profileSuccess}
						</div>
					{/if}

					<!-- Submit Button -->
					<div class="pt-4">
						<button
							type="submit"
							disabled={profileSaving}
							class="w-full px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-400 text-white font-medium rounded-lg transition-colors"
						>
							{profileSaving ? 'Saving...' : $i18n.t('Save Changes')}
						</button>
					</div>
				</form>
			</div>
		{/if}

		<!-- Password Tab -->
		{#if activeTab === 'password'}
			<div class="p-6">
				<form on:submit|preventDefault={handlePasswordChange} class="space-y-4">
					<!-- Current Password Input -->
					<div>
						<label for="currentPassword" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
							{$i18n.t('Current Password')}
						</label>
						<input
							id="currentPassword"
							type="password"
							bind:value={currentPassword}
							placeholder={$i18n.t('Enter your current password')}
							class="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white placeholder-gray-400 dark:placeholder-gray-500 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
						/>
					</div>

					<!-- New Password Input -->
					<div>
						<label for="newPassword" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
							{$i18n.t('New Password')}
						</label>
						<input
							id="newPassword"
							type="password"
							bind:value={newPassword}
							placeholder={$i18n.t('Enter your new password')}
							class="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white placeholder-gray-400 dark:placeholder-gray-500 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
						/>
						<p class="text-xs text-gray-500 dark:text-gray-400 mt-1">
							{$i18n.t('Password must be at least 8 characters long')}
						</p>
					</div>

					<!-- Confirm Password Input -->
					<div>
						<label for="confirmPassword" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
							{$i18n.t('Confirm Password')}
						</label>
						<input
							id="confirmPassword"
							type="password"
							bind:value={confirmPassword}
							placeholder={$i18n.t('Confirm your new password')}
							class="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white placeholder-gray-400 dark:placeholder-gray-500 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
						/>
					</div>

					<!-- Error Message -->
					{#if passwordError}
						<div class="p-3 bg-red-100 dark:bg-red-900 text-red-700 dark:text-red-200 rounded-lg text-sm">
							{passwordError}
						</div>
					{/if}

					<!-- Success Message -->
					{#if passwordSuccess}
						<div class="p-3 bg-green-100 dark:bg-green-900 text-green-700 dark:text-green-200 rounded-lg text-sm">
							{passwordSuccess}
						</div>
					{/if}

					<!-- Submit Button -->
					<div class="pt-4">
						<button
							type="submit"
							disabled={passwordSaving}
							class="w-full px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-400 text-white font-medium rounded-lg transition-colors"
						>
							{passwordSaving ? 'Updating...' : $i18n.t('Change Password')}
						</button>
					</div>
				</form>
			</div>
		{/if}
	</div>
{/if}
