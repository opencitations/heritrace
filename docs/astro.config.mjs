// @ts-check
import { defineConfig } from 'astro/config';
import starlight from '@astrojs/starlight';
import starlightImageZoom from 'starlight-image-zoom';

// https://astro.build/config
export default defineConfig({
	integrations: [
		starlight({
			title: 'HERITRACE',
			description: 'Heritage Enhanced Repository Interface for Tracing, Research, Archival Curation, and Engagement',
			logo: {
				src: './src/assets/logo.png',
				alt: 'HERITRACE logo',
			},
			plugins: [
				starlightImageZoom(),
			],
			social: [
				{ 
					icon: 'github', 
					label: 'GitHub', 
					href: 'https://github.com/opencitations/heritrace' 
				},
			],
			sidebar: [
				{
					label: 'Getting Started',
					items: [
						{ label: 'Introduction', slug: 'introduction' },
						{ label: 'Quick Start', slug: 'getting-started/quick-start' },
					],
				},
				{
					label: 'User Guide',
					items: [
						{ label: 'Overview', slug: 'user-guide/overview' },
						{ label: 'Browsing the Catalogue', slug: 'user-guide/browsing-catalogue' },
						{ label: 'Creating Records', slug: 'user-guide/creating-records' },
						{ label: 'Editing Records', slug: 'user-guide/editing-records' },
						{ label: 'Tracking Changes', slug: 'user-guide/tracking-changes' },
						{ label: 'Merging Records', slug: 'user-guide/merging-records' },
						{ label: 'Using the Time Vault', slug: 'user-guide/time-vault' },
					],
				},
				{
					label: 'Configuration',
					items: [
						{ label: 'Application Settings', slug: 'configuration/app-settings' },
						{ label: 'SHACL Schema', slug: 'configuration/shacl' },
						{ label: 'Display Rules', slug: 'configuration/display-rules' },
					],
				},
				{
					label: 'Testing',
					items: [
						{ label: 'Running Tests', slug: 'testing/running-tests' },
						{ label: 'CI/CD Pipeline', slug: 'testing/cicd' },
					],
				},
			],
		}),
	],
});
