import type { Config } from "tailwindcss";

export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        stone: {
          50: "#fafaf9",
          100: "#f5f5f4",
          200: "#e7e5e4",
          300: "#d6d3d1",
          400: "#a8a29e",
          500: "#78716c",
          600: "#57534e",
          700: "#44403c",
          800: "#292524",
          900: "#1c1917",
        },
      },
      fontFamily: {
        sans: [
          '-apple-system',
          'BlinkMacSystemFont',
          '"SF Pro Display"',
          '"PingFang SC"',
          'sans-serif',
        ],
      },
      backdropBlur: {
        glass: "20px",
      },
      backgroundImage: {
        "glass-card":
          "linear-gradient(135deg, rgba(255,255,255,0.72) 0%, rgba(255,255,255,0.48) 100%)",
        "glass-nav":
          "linear-gradient(180deg, rgba(250,250,249,0.92) 0%, rgba(250,250,249,0.72) 100%)",
      },
      boxShadow: {
        glass: "0 8px 32px rgba(0, 0, 0, 0.04), 0 1px 2px rgba(0, 0, 0, 0.06)",
        "glass-lg": "0 16px 48px rgba(0, 0, 0, 0.06), 0 2px 4px rgba(0, 0, 0, 0.08)",
      },
      keyframes: {
        shimmer: {
          "0%": { backgroundPosition: "-200% 0" },
          "100%": { backgroundPosition: "200% 0" },
        },
      },
      animation: {
        shimmer: "shimmer 1.5s ease-in-out infinite",
      },
    },
  },
  plugins: [],
} satisfies Config;
