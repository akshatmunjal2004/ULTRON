// vite.config.js runs in Node, so it gets Node globals in a dedicated block below.
import js from '@eslint/js';
import react from 'eslint-plugin-react';
import reactHooks from 'eslint-plugin-react-hooks';

export default [
  { ignores: ['dist/**', 'node_modules/**'] },
  js.configs.recommended,
  {
    files: ['vite.config.js', 'eslint.config.js', 'postcss.config.js', 'tailwind.config.js'],
    languageOptions: {
      globals: { process: 'readonly' },
    },
  },
  {
    files: ['src/**/*.{js,jsx}'],
    languageOptions: {
      ecmaVersion: 2022,
      sourceType: 'module',
      parserOptions: { ecmaFeatures: { jsx: true } },
      globals: {
        window: 'readonly',
        document: 'readonly',
        navigator: 'readonly',
        localStorage: 'readonly',
        setTimeout: 'readonly',
        clearTimeout: 'readonly',
        setInterval: 'readonly',
        clearInterval: 'readonly',
        console: 'readonly',
        fetch: 'readonly',
        FormData: 'readonly',
        Blob: 'readonly',
        DOMException: 'readonly',
        AbortController: 'readonly',
        TextDecoder: 'readonly',
        crypto: 'readonly',
        SpeechSynthesisUtterance: 'readonly',
        DataView: 'readonly',
        ArrayBuffer: 'readonly',
        Float32Array: 'readonly',
        MediaRecorder: 'readonly',
        URLSearchParams: 'readonly',
      },
    },
    plugins: { react, 'react-hooks': reactHooks },
    settings: { react: { version: 'detect' } },
    rules: {
      ...react.configs.recommended.rules,
      ...reactHooks.configs.recommended.rules,
      'react/react-in-jsx-scope': 'off',
      'react/prop-types': 'off',
      'no-unused-vars': ['warn', { argsIgnorePattern: '^_' }],
    },
  },
];
