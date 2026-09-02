import vue from "@vitejs/plugin-vue";
import frappeui from "frappe-ui/vite";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [vue(), frappeui({ buildConfig: false, frappeProxy: false, jinjaBootData: false })],
  server: {
    port: Number(process.env.WEB_PORT ?? 3100),
    proxy: {
      "/api": process.env.VITE_API_URL ?? "http://localhost:8100"
    }
  },
  test: {
    environment: "jsdom",
    setupFiles: "./tests/setup.ts"
  }
});
