import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  darkMode: "media",
  theme: {
    extend: {
      colors: {
        brand: {
          start: "#667eea",
          mid: "#764ba2",
          end: "#f093fb",
        },
      },
      backgroundImage: {
        "brand-gradient": "linear-gradient(135deg, #667eea 0%, #764ba2 50%, #f093fb 100%)",
        "brand-gradient-soft": "linear-gradient(135deg, #667eea 0%, #764ba2 100%)",
      },
    },
  },
  plugins: [],
};

export default config;
