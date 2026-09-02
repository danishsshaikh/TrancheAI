import type { Config } from "tailwindcss";
import preset from "frappe-ui/tailwind";

export default {
  presets: [preset],
  content: [
    "./index.html",
    "./src/**/*.{ts,vue}",
    "./node_modules/frappe-ui/src/**/*.{js,ts,vue}"
  ],
  theme: {
    extend: {
      colors: {
        background: "oklch(98% 0.006 210)",
        panel: "oklch(100% 0 0)",
        foreground: "oklch(22% 0.018 230)",
        muted: "oklch(47% 0.016 230)",
        line: "oklch(88% 0.011 230)",
        primary: "oklch(47% 0.12 188)",
        accent: "oklch(53% 0.16 35)",
        success: "oklch(48% 0.12 150)",
        warning: "oklch(61% 0.13 75)",
        danger: "oklch(55% 0.16 25)",
        violet: "oklch(50% 0.13 292)"
      }
    }
  },
  plugins: []
} satisfies Config;
