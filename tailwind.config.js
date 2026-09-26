/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      fontFamily: {
        mono: ['"JetBrains Mono"', '"SFMono-Regular"', 'monospace'],
      },
      colors: {
        cyber: {
          cyan: '#00f0ff',
          green: '#8cff9c',
          black: '#050508',
          panel: '#0d1117',
        },
      },
    },
  },
  plugins: [],
};
