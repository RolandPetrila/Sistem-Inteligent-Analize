/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        dark: {
          bg: "#1a1a2e",
          surface: "#16213e",
          card: "#1e2a4a",
          border: "#2a3a5c",
          hover: "#253555",
        },
        accent: {
          primary: "#6366f1",
          secondary: "#818cf8",
          light: "#a5b4fc",
          glow: "#4f46e5",
        },
        trust: {
          oficial: "#00AA00",
          verificat: "#0066CC",
          estimat: "#FF8800",
          neconcludent: "#CC0000",
          indisponibil: "#888888",
        },
        risk: {
          verde: "#22c55e",
          galben: "#eab308",
          rosu: "#ef4444",
        },
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
        mono: ["JetBrains Mono", "monospace"],
      },
    },
  },
  plugins: [],
};
