import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        bg: "#f7f6f2",
        ink: "#1a1a18",
        muted: "#6b6a63",
        border: "#e3e0d6",
        accent: "#0b6e4f",
        caveat: "#fdf3e0",
        "caveat-ink": "#92400e",
        "caveat-border": "#f0d9a8",
      },
    },
  },
  plugins: [],
};

export default config;
