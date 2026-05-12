import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{ts,tsx}",
    "./lib/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        teal: {
          deep: "#0A2A2E",
          deeper: "#061d20",
          slate: "#11393d",
          slateLight: "#174247",
        },
        coral: {
          DEFAULT: "#FF8D6E",
          muted: "#cf6f56",
        },
        sand: {
          DEFAULT: "#E0D3C8",
          muted: "#a89a8e",
          dim: "#7a6e63",
        },
      },
      fontFamily: {
        serif: ["var(--font-serif)", "ui-serif", "Georgia", "serif"],
        sans: ["var(--font-sans)", "ui-sans-serif", "system-ui", "sans-serif"],
        mono: ["var(--font-mono)", "ui-monospace", "SFMono-Regular", "monospace"],
      },
      backgroundImage: {
        grid:
          "linear-gradient(to right, rgba(224,211,200,0.04) 1px, transparent 1px), linear-gradient(to bottom, rgba(224,211,200,0.04) 1px, transparent 1px)",
      },
      transitionTimingFunction: {
        "ease-out-soft": "cubic-bezier(0.22, 1, 0.36, 1)",
      },
    },
  },
  plugins: [],
};

export default config;
