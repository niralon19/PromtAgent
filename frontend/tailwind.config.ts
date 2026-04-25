import type { Config } from 'tailwindcss';

const config: Config = {
  darkMode: ['class'],
  content: [
    './pages/**/*.{js,ts,jsx,tsx,mdx}',
    './components/**/*.{js,ts,jsx,tsx,mdx}',
    './app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        critical: 'var(--color-critical)',
        warning: 'var(--color-warning)',
        investigating: 'var(--color-investigating)',
        resolved: 'var(--color-resolved)',
        info: 'var(--color-info)',
      },
    },
  },
  plugins: [],
};

export default config;
