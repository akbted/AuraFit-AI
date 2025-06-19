/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,jsx}",
  ],
  theme: {
    extend: {
      colors: {
        primary: '#646cff',
        primaryHover: '#535bf2',
        background: '#242424',
        backgroundLight: '#ffffff',
        text: 'rgba(255, 255, 255, 0.87)',
        textLight: '#213547'
      },
    },
  },
  plugins: [],
}