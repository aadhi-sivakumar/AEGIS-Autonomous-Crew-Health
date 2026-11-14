import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        aegis: {
          bg: "#0B1420",
          panel: "#142337",
          border: "#2C4157",
          text: "#E7EEF5",
          muted: "#A9B9CB",
          cyan: "#55B8E8",
          amber: "#E6AD57",
          red: "#D96767",
          green: "#53BE8B",
        },
      },
      fontFamily: {
        sans: ["var(--font-ibm-plex-sans)", "system-ui", "sans-serif"],
        mono: ["var(--font-ibm-plex-mono)", "ui-monospace", "monospace"],
      },
      borderRadius: {
        panel: "8px",
      },
      spacing: {
        grid: "8px",
      },
    },
  },
  plugins: [],
};
export default config;
