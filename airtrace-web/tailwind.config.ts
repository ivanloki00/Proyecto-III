import type { Config } from 'tailwindcss'

// Tailwind v4 uses @theme in CSS (src/index.css) as the primary config mechanism.
// This file is kept for tooling compatibility (shadcn/ui CLI, editor plugins).
const config: Config = {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        'score-a': '#00c864',
        'score-b': '#c8e632',
        'score-c': '#ffc800',
        'score-d': '#ff8200',
        'score-e': '#e63232',
        'score-f': '#960096',
        background: '#0f1117',
        surface: '#1a1d27',
        border: '#2d3142',
        accent: '#3b82f6',
      },
    },
  },
  plugins: [],
}

export default config
