import { defineConfig, type Plugin } from 'vite'
import react, { reactCompilerPreset } from '@vitejs/plugin-react'
import babel from '@rolldown/plugin-babel'
import { createRequire } from 'node:module'
import { readFileSync } from 'node:fs'
import { dirname, join } from 'node:path'

// pdf.js ships its JPEG2000 (openjpeg) and ICC color (qcms) decoders as separate
// WASM modules and only loads them when given a `wasmUrl`. Without openjpeg.wasm,
// JPEG2000-encoded pages (i.e. scanned documents) fail to decode and render blank.
// This serves both files at /wasm/ — straight from the installed pdfjs-dist, so the
// WASM version always matches the package (no CDN, no manual copy, no version drift).
function pdfjsWasm(): Plugin {
  const require = createRequire(import.meta.url)
  const wasmDir = join(dirname(require.resolve('pdfjs-dist/package.json')), 'wasm')
  const files = ['openjpeg.wasm', 'qcms_bg.wasm']
  return {
    name: 'pdfjs-wasm',
    // Dev: stream the files from node_modules on request.
    configureServer(server) {
      server.middlewares.use((req, res, next) => {
        const file = files.find((f) => req.url === `/wasm/${f}`)
        if (!file) return next()
        res.setHeader('Content-Type', 'application/wasm')
        res.end(readFileSync(join(wasmDir, file)))
      })
    },
    // Build: emit the files into the output at /wasm/.
    generateBundle() {
      for (const file of files) {
        this.emitFile({ type: 'asset', fileName: `wasm/${file}`, source: readFileSync(join(wasmDir, file)) })
      }
    },
  }
}

// https://vite.dev/config/
export default defineConfig({
  plugins: [
    react(),
    babel({ presets: [reactCompilerPreset()] }),
    pdfjsWasm(),
  ],
})
