import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  build: {
    // Source maps: full in dev, hidden in production
    sourcemap: process.env.NODE_ENV === 'development' ? true : 'hidden',

    // Optimize chunk splitting for better caching
    rollupOptions: {
      output: {
        manualChunks: {
          // Vendor chunk for React and core libraries
          'vendor-react': [
            'react',
            'react-dom',
            'react-router-dom',
          ],
          // UI library chunk
          'vendor-ui': [
            'lucide-react',
            '@radix-ui/react-dialog',
            '@radix-ui/react-label',
            '@radix-ui/react-select',
            '@radix-ui/react-slot',
            '@radix-ui/react-toast',
          ],
          // Charting library chunk (if used)
          'vendor-charts': [
            'recharts',
          ],
        },
        // Consistent chunk naming for better caching
        chunkFileNames: 'assets/[name]-[hash].js',
        entryFileNames: 'assets/[name]-[hash].js',
        assetFileNames: 'assets/[name]-[hash].[ext]',
      },
    },

    // Optimize bundle size
    minify: 'esbuild',
    target: 'esnext',
  },
})
