import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./lib/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        medPink: {
          50: "#fdf2f5",
          100: "#fae1e9",
          200: "#f6c8d7",
          300: "#f0a3bd",
          400: "#e98baa", // Primary brand accent
          500: "#d97394",
          600: "#c45479",
          700: "#a63f60",
          800: "#8b3652",
          900: "#753147",
        },
        medTeal: {
          50: "#f0fdfa",
          100: "#ccfbf1",
          200: "#99f6e4",
          300: "#5eead4",
          400: "#2bb7a9", // Secondary medical accent
          500: "#20a396",
          600: "#178278",
          700: "#176760",
          800: "#17524e",
          900: "#174441",
        },
        medSlate: {
          50: "#f8fafc",
          100: "#f1f5f9",
          200: "#e2e8f0",
          300: "#cbd5e1",
          400: "#94a3b8",
          500: "#64748b",
          600: "#475569",
          700: "#334155",
          800: "#1e293b",
          900: "#172033", // Dark text
        },
      },
    },
  },
  plugins: [],
};
export default config;
