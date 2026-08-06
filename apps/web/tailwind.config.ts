import type { Config } from "tailwindcss";

export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        surface: "oklch(98% 0.006 165)",
        background: "oklch(98% 0.006 165)",
        panel: "oklch(94% 0.01 170)",
        foreground: "oklch(22% 0.025 165)",
        ink: "oklch(22% 0.025 165)",
        muted: "oklch(46% 0.018 165)",
        border: "oklch(85% 0.012 165)",
        line: "oklch(85% 0.012 165)",
        primary: "oklch(48% 0.13 170)",
        accent: "oklch(48% 0.13 170)",
        success: "oklch(48% 0.12 150)",
        warning: "oklch(61% 0.13 75)",
        danger: "oklch(55% 0.16 25)"
      }
    }
  },
  plugins: []
} satisfies Config;
