# =============================================================================
# AgentMesh Frontend — Multi-stage production Dockerfile
# Stage 1: Build with Node, Stage 2: Serve with nginx
# =============================================================================

# ---- Build Stage ----
FROM node:20-alpine AS builder

WORKDIR /app

COPY package*.json ./
RUN npm ci --prefer-offline

COPY . .

# Build for production; VITE_API_URL injected at build time
ARG VITE_API_URL=http://localhost:8000
ENV VITE_API_URL=$VITE_API_URL
RUN npm run build

# ---- Serve Stage ----
FROM nginx:1.27-alpine AS production

# Copy built assets
COPY --from=builder /app/dist /usr/share/nginx/html

# nginx config: SPA routing + API proxy to backend
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

HEALTHCHECK --interval=15s --timeout=5s --retries=3 \
    CMD wget -qO- http://localhost:80 || exit 1

CMD ["nginx", "-g", "daemon off;"]
