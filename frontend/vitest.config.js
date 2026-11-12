import { defineConfig } from 'vitest/config';

// Vitest runs pure modules only (plan.md §12.1, Q.2's Front lane): plain .js files under src/, in Node, with no DOM
// and no components. Screens are proved by the Look and Walk lanes instead.
export default defineConfig({
  test: {
    include: ['src/**/*.test.js'],
    environment: 'node',
    restoreMocks: true,
  },
});
