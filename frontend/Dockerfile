# ── Stage 1: Build ──────────────────────────────────────────────────────────
FROM node:20-alpine AS builder

WORKDIR /app

# Copiar deps primero (aprovecha cache de Docker)
COPY package*.json ./
RUN npm ci --no-audit --no-fund

# Build args (vienen de EasyPanel env vars)
ARG VITE_SUPABASE_URL
ARG VITE_SUPABASE_ANON_KEY
ARG VITE_N8N_BASE
ARG VITE_N8N_WEBHOOK_INTERNO
ARG VITE_N8N_WEBHOOK_ANALISTA
ARG VITE_CONTRATOS_API
ARG VITE_ADMIN_USERNAME
ARG VITE_ADMIN_PASSWORD

ENV VITE_SUPABASE_URL=$VITE_SUPABASE_URL
ENV VITE_SUPABASE_ANON_KEY=$VITE_SUPABASE_ANON_KEY
ENV VITE_N8N_BASE=$VITE_N8N_BASE
ENV VITE_N8N_WEBHOOK_INTERNO=$VITE_N8N_WEBHOOK_INTERNO
ENV VITE_N8N_WEBHOOK_ANALISTA=$VITE_N8N_WEBHOOK_ANALISTA
ENV VITE_CONTRATOS_API=$VITE_CONTRATOS_API
ENV VITE_ADMIN_USERNAME=$VITE_ADMIN_USERNAME
ENV VITE_ADMIN_PASSWORD=$VITE_ADMIN_PASSWORD

# Copiar código y buildear
COPY . .
RUN npm run build

# ── Stage 2: Nginx ──────────────────────────────────────────────────────────
FROM nginx:1.27-alpine

# Config nginx para SPA (React Router)
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Copiar el build de Vite
COPY --from=builder /app/dist /usr/share/nginx/html

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
