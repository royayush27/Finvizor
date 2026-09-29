import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        slate: { 50: '#f6f5f0', 100: '#eeeee7', 200: '#dcded5', 300: '#c7ccc1', 400: '#889084', 500: '#68716a', 600: '#535e54', 700: '#3d4a40', 800: '#303d34', 900: '#242f2b', 950: '#17231d' },
        emerald: { 50: '#edf2e9', 100: '#e3ebdd', 300: '#a9bc9e', 500: '#4c7855', 600: '#386543', 700: '#2d573d', 900: '#245744' },
      },
    },
  },
  plugins: [],
};

export default config;
