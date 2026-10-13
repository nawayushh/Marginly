// Vite configuration for the Marginly frontend.
// The dev server runs on port 5173, which is the one origin the backend allows via CORS.
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    strictPort: true, // fail loudly instead of silently moving to another port (CORS would break)
  },
});
