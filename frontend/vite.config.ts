import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    port: 5173,
  },
  preview: {
    // Sem isto, `vite preview` recusa qualquer requisição cujo Host não seja
    // localhost — bloquearia todo tráfego real batendo no domínio público do
    // Railway. Sem segredo nenhum nesta camada (só serve o `dist/` estático),
    // então liberar geral aqui não expõe nada que o build não expusesse já.
    allowedHosts: true,
  },
})
