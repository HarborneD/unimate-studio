import { defineConfig } from 'vite';
export default defineConfig({
  build: { outDir: 'build/web' },
  server: { proxy: { '/api': 'http://127.0.0.1:8170' } }
});
