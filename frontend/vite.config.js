import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// ✅ Must export the result of defineConfig()
export default defineConfig({
  plugins: [react()],
  server: {
    host: '0.0.0.0',
    port: 5173,
    strictPort: true,
    // Proxy API requests to backend during development
    proxy: {
      '/api': {
        target: 'http://backend:8000',
        changeOrigin: true,
        secure: false,
      }
    }
  },
  // Optional: Build configuration
  build: {
    outDir: 'dist',
    sourcemap: true,
  }
});