import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5174,
    headers: {
      // Increase max header size to prevent 431 errors
    },
  },
})

// Note: If you still see 431 errors, run the dev server with increased header size:
// NODE_OPTIONS='--max-http-header-size=32768' npm run dev
