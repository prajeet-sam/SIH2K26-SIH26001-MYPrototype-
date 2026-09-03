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
        'risk-low': '#22c55e',
        'risk-moderate': '#eab308',
        'risk-high': '#f97316',
        'risk-critical': '#ef4444',
        'dashboard-bg': '#0f172a',
        'dashboard-card': '#1e293b',
        'dashboard-accent': '#0891b2',
        'dashboard-border': '#334155',
      },
      backgroundImage: {
        'gradient-radial': 'radial-gradient(var(--tw-gradient-stops))',
        'gradient-conic': 'conic-gradient(from 180deg at 50% 50%, var(--tw-gradient-stops))',
      },
    },
  },
  plugins: [],
}
