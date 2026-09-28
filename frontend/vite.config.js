import path from 'node:path'
import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: {
      '@': path.resolve(import.meta.dirname, './src'),
    },
  },
  // Vitest reads this same config (npm run test / `vitest run`) — no
  // separate vitest.config.js, so the `@` alias above is shared instead of
  // duplicated. `environment: 'node'` is enough for the pure-logic tests
  // this repo has today (fix/approver-can-open-tests, src/lib/*.test.js) —
  // switch to 'jsdom' (an added devDependency) only once a test needs to
  // actually render a component.
  test: {
    environment: 'node',
    include: ['src/**/*.test.js'],
  },
})
