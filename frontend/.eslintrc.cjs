module.exports = {
	root: true,
	extends: [
		'eslint:recommended',
		'plugin:@typescript-eslint/strict-type-checked',
		'plugin:@typescript-eslint/stylistic-type-checked',
		'plugin:svelte/recommended',
		'prettier'
	],
	parser: '@typescript-eslint/parser',
	plugins: ['@typescript-eslint'],
	parserOptions: {
		sourceType: 'module',
		ecmaVersion: 2020,
		extraFileExtensions: ['.svelte'],
		project: './tsconfig.json'
	},
	env: {
		browser: true,
		es2017: true,
		node: true
	},
	overrides: [
		{
			files: ['*.svelte'],
			parser: 'svelte-eslint-parser',
			parserOptions: {
				parser: '@typescript-eslint/parser'
			}
		}
	],
	rules: {
		// Strict type safety - no any allowed
		'@typescript-eslint/no-explicit-any': 'error',
		'@typescript-eslint/no-unsafe-argument': 'error',
		'@typescript-eslint/no-unsafe-assignment': 'error',
		'@typescript-eslint/no-unsafe-call': 'error',
		'@typescript-eslint/no-unsafe-member-access': 'error',
		'@typescript-eslint/no-unsafe-return': 'error',

		// Strict null checks
		'@typescript-eslint/strict-boolean-expressions': [
			'error',
			{
				allowString: true,
				allowNumber: true,
				allowNullableObject: true,
				allowNullableBoolean: true,
				allowNullableString: true,
				allowNullableNumber: false
			}
		],

		// Best practices
		'@typescript-eslint/explicit-function-return-type': [
			'error',
			{
				allowExpressions: true,
				allowTypedFunctionExpressions: true,
				allowHigherOrderFunctions: true,
				allowDirectConstAssertionInArrowFunctions: true,
				allowConciseArrowFunctionExpressionsStartingWithVoid: true
			}
		],
		'@typescript-eslint/explicit-module-boundary-types': 'error',
		'@typescript-eslint/no-unused-vars': [
			'error',
			{
				argsIgnorePattern: '^_',
				varsIgnorePattern: '^_',
				caughtErrorsIgnorePattern: '^_'
			}
		],

		// Additional strict rules
		'@typescript-eslint/prefer-nullish-coalescing': 'error',
		'@typescript-eslint/prefer-optional-chain': 'error',
		'@typescript-eslint/no-floating-promises': 'error',
		'@typescript-eslint/no-misused-promises': 'error',
		'@typescript-eslint/await-thenable': 'error',
		'@typescript-eslint/require-await': 'error',
		'@typescript-eslint/no-unnecessary-condition': 'error',
		'@typescript-eslint/no-unnecessary-type-assertion': 'error',
		'@typescript-eslint/prefer-as-const': 'error',
		'@typescript-eslint/consistent-type-imports': [
			'error',
			{ prefer: 'type-imports', fixStyle: 'separate-type-imports' }
		],
		'@typescript-eslint/consistent-type-exports': 'error',

		// Require types everywhere
		'@typescript-eslint/typedef': [
			'error',
			{
				arrayDestructuring: false,
				arrowParameter: false,
				memberVariableDeclaration: true,
				objectDestructuring: false,
				parameter: true,
				propertyDeclaration: true,
				variableDeclaration: false,
				variableDeclarationIgnoreFunction: true
			}
		],

		// General code quality
		'no-console': ['warn', { allow: ['warn', 'error'] }],
		'no-debugger': 'error',
		'prefer-const': 'error',
		'no-var': 'error',
		eqeqeq: ['error', 'always'],
		curly: ['error', 'all']
	},
	ignorePatterns: ['*.cjs', 'svelte.config.js', 'vite.config.ts', 'playwright.config.ts']
};
