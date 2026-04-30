/** @type {import('tailwindcss').Config} */
export default {
  darkMode: ["class"],
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        border: "#E5E7EB",
        background: "#F8F9FB",
        foreground: "#111827",
        primary: {
          DEFAULT: "#6366F1",
          foreground: "#FFFFFF",
        },
        muted: {
          DEFAULT: "#F3F4F6",
          foreground: "#6B7280",
        },
        destructive: {
          DEFAULT: "#EF4444",
          foreground: "#FFFFFF",
        },
      },
      borderRadius: {
        xl: "12px",
      },
      boxShadow: {
        card: "0 1px 4px rgba(0,0,0,0.06)",
        float: "0 18px 48px rgba(17,24,39,0.18)",
      },
      fontFamily: {
        sans: ["Inter", "Noto Sans SC", "sans-serif"],
      },
    },
  },
  plugins: [],
};
