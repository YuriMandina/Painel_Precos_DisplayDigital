/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        primary: "#2C1A12",
        accent: "#C48B57",
        background: "#F9F6F0",
        textMain: "#1A1A1A",
      },
      fontFamily: {
        heading: ['"Playfair Display"', 'serif'],
        body: ['Inter', 'sans-serif'],
      }
    },
  },
  plugins: [],
}
