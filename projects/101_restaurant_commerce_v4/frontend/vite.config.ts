import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
export default defineConfig({
  plugins: [react()],
  base: "/workspace-assets/",
  build: {
    outDir: "../src/world_model/restaurant_commerce/web/workspace",
    emptyOutDir: true,
    manifest: true,
  },
  server: { proxy: { "/api": "http://127.0.0.1:8806" } },
});
