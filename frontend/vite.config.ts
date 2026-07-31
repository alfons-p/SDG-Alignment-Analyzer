import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    // Bind IPv4 explicitly. Vite's default `localhost` resolves to IPv6 ::1
    // only, but cloudflared connects to 127.0.0.1 — mismatch = tunnel 502.
    host: '127.0.0.1',
    // Allow the Cloudflare tunnel hostname through Vite's host check.
    allowedHosts: ['sdg.alnura.app'],
    // HMR websocket runs over the tunnel on 443 (wss inferred from https).
    hmr: { clientPort: 443 },
  },
})
