/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./core/templates/**/*.html",
    "./core/forms.py",
  ],
  theme: {
    extend: {
      colors: {
        cream: {
          50: '#FFFDF5',
          100: '#F5F5DC',
        },
        brown: {
          700: '#5D4037',
          800: '#4E342E',
          950: '#2D1B16',
        },
        orange: {
          500: '#FF8C00',
          600: '#E67E22',
          700: '#D35400',
        },
        shaolin: {
          red: '#C53030', // Rojo vibrante del logo
        }
      },
      fontFamily: {
        sans: ['Montserrat', 'Roboto', 'sans-serif'],
      },
    },
  },
  plugins: [],
}
