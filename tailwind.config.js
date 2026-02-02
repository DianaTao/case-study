/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './pages/**/*.{js,ts,jsx,tsx,mdx}',
    './components/**/*.{js,ts,jsx,tsx,mdx}',
    './app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        partselect: {
          // Main brand color (used by bg-partselect-primary, text-partselect-primary, etc.)
          primary: '#467576',
          secondary: '#5f6368',
          accent: '#ea4335',
          success: '#34a853',
          warning: '#fbbc04',
          background: '#ffffff',
          surface: '#f8f9fa',
          border: '#dadce0',
          text: {
            primary: '#202124',
            secondary: '#5f6368',
            disabled: '#9aa0a6',
          },
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
      },
    },
  },
  plugins: [],
}
