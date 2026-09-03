import vue from "@vitejs/plugin-vue";
import frappeui from "frappe-ui/vite";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [frappeui({ lucideIcons: true, buildConfig: false, frappeProxy: false, jinjaBootData: false }), vue()],
  server: {
    port: Number(process.env.WEB_PORT ?? 3100),
    proxy: {
      "/api": process.env.VITE_API_URL ?? "http://localhost:8100"
    }
  },
  optimizeDeps: {
    exclude: ["frappe-ui"],
    include: [
      "feather-icons",
      "tippy.js",
      "engine.io-client",
      "socket.io-client",
      "debug"
    ]
  },
  test: {
    environment: "jsdom",
    setupFiles: "./tests/setup.ts"
  }
});
