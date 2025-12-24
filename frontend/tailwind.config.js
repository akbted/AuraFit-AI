/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        cyber: {
          darker: '#0a0a0f',
          dark: '#12121a',
          medium: '#1a1a2e',
          light: '#252540',
          accent: '#00d4ff',
          'accent-alt': '#7c3aed',
          success: '#10b981',
          warning: '#f59e0b',
          error: '#ef4444',
        }
      },
      fontFamily: {
        body: ['Inter', 'system-ui', '-apple-system', 'sans-serif'],
        display: ['Orbitron', 'monospace'],
        ui: ['Rajdhani', 'sans-serif'],
      },
    },
  },
  plugins: [],
}
