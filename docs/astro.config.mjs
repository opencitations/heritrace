// @ts-check
import { defineConfig } from 'astro/config';
import starlight from '@astrojs/starlight';
import starlightImageZoom from 'starlight-image-zoom';

// https://astro.build/config
export default defineConfig({
	site: 'https://opencitations.github.io',
	base: '/heritrace',
	integrations: [
		starlight({
			title: 'HERITRACE',
			description: 'Heritage Enhanced Repository Interface for Tracing, Research, Archival Curation, and Engagement',
			logo: {
				src: './src/assets/logo.png',
				alt: 'HERITRACE logo',
			},
			expressiveCode: {
				shiki: {
					// Map 'ttl' to use 'sparql' highlighting
					langAlias: {
						'ttl': 'sparql',
						'turtle': 'sparql'
					}
				}
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
					label: 'Getting started',
					items: [
						{ label: 'Introduction', slug: 'introduction' },
						{ label: 'Quick start', slug: 'getting-started/quick-start' },
					],
				},
				{
					label: 'User guide',
					items: [
						{ label: 'Overview', slug: 'user-guide/overview' },
						{ label: 'Browsing the catalogue', slug: 'user-guide/browsing-catalogue' },
						{ label: 'Creating new records', slug: 'user-guide/creating-records' },
						{ label: 'Editing existing records', slug: 'user-guide/editing-records' },
						{ label: 'Tracking changes', slug: 'user-guide/tracking-changes' },
						{ label: 'Merging records', slug: 'user-guide/merging-records' },
						{ label: 'Using the time vault', slug: 'user-guide/time-vault' },
					],
				},
				{
					label: 'Configuration',
					items: [
						{ label: 'Application settings', slug: 'configuration/app-settings' },
						{ label: 'SHACL configuration', slug: 'configuration/shacl' },
						{ label: 'Display rules configuration', slug: 'configuration/display-rules' },
					],
				},
				{
					label: 'Development',
					items: [
						{ label: 'Development setup', slug: 'development' },
						{ label: 'Running tests', slug: 'testing/running-tests' },
						{ label: 'CI/CD pipeline', slug: 'testing/cicd' },
					],
				},
			],
		}),
	],
});
