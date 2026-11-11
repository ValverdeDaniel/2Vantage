import react from '@vitejs/plugin-react';
import { defineConfig } from 'vite';

// plan.md §3.4. The proxy keeps the SPA and the API on one origin, so the session cookie works unchanged (§3.8).
const target = process.env.VITE_API_PROXY || 'http://localhost:8004';

// changeOrigin stays false: the browser's Host (localhost:4001) reaches Django, so its CSRF Origin check matches.
// /static carries the CSS of Django's own pages (admin, password change); without it they arrive unstyled.
const proxy = Object.fromEntries(
  ['/api', '/admin', '/accounts', '/static'].map((path) => [path, { target, changeOrigin: false }]),
);

export default defineConfig({
  plugins: [react()],
  server: {
    port: 4001,
    strictPort: true,
    host: true,
    // File-change events from a Windows host do not reliably reach containers.
    watch: { usePolling: true, interval: 300 },
    proxy,
  },
});
