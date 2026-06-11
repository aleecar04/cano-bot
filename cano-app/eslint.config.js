// https://docs.expo.dev/guides/using-eslint/
const { defineConfig } = require('eslint/config');
const expoConfig = require('eslint-config-expo/flat');

module.exports = defineConfig([
  expoConfig,
  {
    ignores: ['dist/*', 'coverage/*'],
  },
  {
    // Los tests usan jest.mock() antes de import del componente, lo cual Jest
    // hoistea automáticamente. ESLint no lo entiende y se queja con import/first.
    files: ['__tests__/**/*.{ts,tsx}'],
    rules: {
      'import/first': 'off',
    },
  },
]);
