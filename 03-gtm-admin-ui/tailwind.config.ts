import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{ts,tsx}",
    "./lib/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        "al-ink": "#1A0A0A",
        "al-cream": "#FBF6EE",
        "al-cream-warm": "#F5E9D7",
        "al-cream-dim": "#EDDFCA",
        "al-red": "#C8102E",
        "al-red-deep": "#7A1421",
        "al-orange": "#E85D2F",
        "al-gold": "#C9A227",
        "al-gold-soft": "#D9B872",
        "al-ink-soft": "#4A2424",
        "al-ink-mute": "#7A5454",
        "al-sand": "#F5E9D7",
        "al-sand-soft": "#C9B79A",
        "al-sand-mute": "#8B7456",
      },
      fontFamily: {
        serif: ["var(--font-fraunces)", "Times New Roman", "Georgia", "serif"],
        sans: ["var(--font-inter)", "IBM Plex Sans", "system-ui", "sans-serif"],
        mono: ["var(--font-plex-mono)", "ui-monospace", "monospace"],
      },
      backgroundImage: {
        "al-grid":
          "linear-gradient(to right, rgba(200,16,46,0.04) 1px, transparent 1px), linear-gradient(to bottom, rgba(200,16,46,0.04) 1px, transparent 1px)",
      },
      transitionTimingFunction: {
        "ease-out-soft": "cubic-bezier(0.22, 1, 0.36, 1)",
      },
    },
  },
  plugins: [],
};

export default config;
