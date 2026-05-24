/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        dark: {
          950: '#070a13',
          900: '#0b0f19',
          800: '#151b2d',
          700: '#1f293d',
          600: '#2d3b55',
          500: '#475a80',
        },
        brand: {
          50: '#f0f6ff',
          100: '#e0edff',
          200: '#bad7ff',
          300: '#7db2ff',
          400: '#388dff',
          500: '#0066ff',
          600: '#004cff',
          700: '#003be6',
          800: '#0030bf',
          900: '#001a73',
        }
      }
    },
  },
  plugins: [],
}
