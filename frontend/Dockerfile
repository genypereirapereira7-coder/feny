FROM node:20-slim

WORKDIR /app

COPY package*.json ./
RUN npm ci

COPY . .

# Vite embute `import.meta.env.VITE_*` em tempo de BUILD, não de runtime —
# sem declarar isto como ARG, a variável que você configurar no serviço do
# Railway nunca chegaria no `npm run build` rodando dentro da imagem. Railway
# repassa toda variável do serviço como build arg automaticamente quando ela
# é declarada com `ARG` de mesmo nome no Dockerfile.
ARG VITE_API_BASE_URL
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL

RUN npm run build

EXPOSE 4173

# $PORT vem do Railway; o script "preview" (package.json) já lê `$PORT` e
# escuta em 0.0.0.0 — sem isso, `vite preview` só aceita conexão local e
# bloqueia qualquer Host que não seja localhost (ver vite.config.ts).
CMD ["npm", "run", "preview"]
