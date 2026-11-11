import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import path from "node:path";
import { defineConfig } from "vite";

// In development the API runs separately; /api is proxied so the browser sees one origin.
const API = process.env.COINNECT_API ?? "http://127.0.0.1:8000";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: { alias: { "@": path.resolve(import.meta.dirname, "src") } },
  server: { port: Number(process.env.PORT ?? 5173), strictPort: true, proxy: Object.fromEntries(["/api", "/docs", "/openapi.json"].map((p) => [p, { target: API, changeOrigin: true }])) },
});
